#!/usr/bin/env python3
"""script to sample repos

Result types:

- type: str (build, notebook, import)
  success: bool
  output: path to log

"""
import argparse
import json
import logging
import os
import sys
import tempfile
from collections import defaultdict
from collections import namedtuple
from datetime import datetime
from subprocess import run
from subprocess import STDOUT
from threading import Thread
from urllib.parse import urlparse

import docker
import repo2docker
import tornado.log
from repo2docker.contentproviders.git import Git

here = os.path.abspath(os.path.dirname(__file__))
log = logging.getLogger(__name__)

now = datetime.now()
timestamp = now.isoformat()
run_id = os.environ.get("RUN_ID", now.strftime("%Y-%m-%dT%H.%M"))

CHUNK_SIZE = 64


def _tee(fd, fname):
    """The part of tee that runs in a background thread"""
    with open(fname, "w") as log_f:
        with os.fdopen(fd, "r") as pipe_f:
            while True:
                chunk = pipe_f.read(CHUNK_SIZE)
                if not chunk:
                    return
                sys.stderr.write(chunk)
                log_f.write(chunk)


def tee(fname):
    """Like command-line tee, but in Python"""
    reader, writer = os.pipe()
    Thread(target=_tee, args=(reader, fname), daemon=True).start()
    return os.fdopen(writer, "w")


def clone_repo(repo, ref):
    """Clone a repo, return checkout path and resolved ref"""
    slug = repo_slug(repo)

    td = tempfile.mkdtemp(prefix=f"r2d-test-{run_id}")
    checkout_path = os.path.join(td, slug)
    try:
        os.makedirs(checkout_path)
    except FileExistsError:
        pass

    cp = Git()
    spec = cp.detect(repo, ref=ref)
    for line in cp.fetch(spec, output_dir=checkout_path, yield_output=sys.stderr.write):
        sys.stderr.write(line)

    resolved_ref = cp.content_id or ref
    return checkout_path, resolved_ref


def build_repo(repo, resolved_ref, checkout_path, build_log_file, force_build=False):
    """build one repo"""

    image_id = make_image_id(repo, resolved_ref)
    d = docker.from_env()
    try:
        image = d.images.get(image_id)
    except docker.errors.ImageNotFound:
        # need to build
        pass
    else:
        log.info(f"Already have image {image_id}")
        if not force_build:
            with open(build_log_file, "w") as f:
                f.write(f"Image {image_id} already built")
            return image_id, checkout_path

    log.info(f"Building image {image_id} for {repo}@{resolved_ref}")

    with tee(build_log_file) as stdout:
        try:
            run(
                [
                    "jupyter-repo2docker",
                    "--no-run",
                    "--no-clean",
                    "--image-name",
                    image_id,
                    checkout_path,
                ],
                stdout=stdout,
                stderr=STDOUT,
                check=True,
            )
        finally:
            stdout.flush()
    return image_id, checkout_path


def find_notebooks(path):
    """Yield all the notebooks in a directory

    Yields the path relative to the given directory
    """
    for parent, dirs, files in os.walk(path):
        for fname in files:
            if fname.endswith(".ipynb"):
                yield os.path.relpath(os.path.join(parent, fname), path)


def run_one_test(image, kind, argument, run_dir):
    d = docker.from_env()
    try:
        for line in d.containers.run(
            image,
            # auto_remove=True,
            detach=False,
            stream=True,
            stdout=False,
            stderr=True,
            environment={"PYTHONUNBUFFERED": "1"},
            volumes={here: {"bind": "/io", "mode": "rw"}},
            command=[
                "python3",
                "-u",
                "/io/inrepo.py",
                "--output-dir",
                os.path.join("/io", os.path.relpath(run_dir, here)),
                kind,
                argument,
            ],
        ):
            print("line!", line, type(line))
            sys.stderr.write(line.decode("utf8"))
    except docker.errors.ContainerError as e:
        sys.stderr.write(e.stderr.decode("utf8"))
        e.container.remove()
        raise
    else:
        # remove
        pass

    return {
        "kind": "notebook",
        "success": True,
        "test_id": argument,
        "path": "x",
    }


def run_tests(image, checkout_path, run_dir):
    """Find tests to run and run them"""
    for nb_path in find_notebooks(checkout_path):
        try:
            yield run_one_test(image, "notebook", nb_path, run_dir)
        except Exception:
            log.exception(f"Error running test {nb_path}")
            yield {
                "kind": "notebook",
                "success": False,
                "test_id": nb_path,
                "path": "x",
            }


def repo_slug(url):
    """return hostname/repo/path for a url"""
    if url.endswith(".git"):
        # strip redundant .git extension
        url = url[:-4]
    urlinfo = urlparse(url)
    return f"{urlinfo.hostname}{urlinfo.path}"
    _, host_path = url.split("://", 1)
    return host_path.replace("/", "-")


def make_image_id(repo, ref):
    """Compute the image for a given repo & ref"""
    slug = repo_slug(repo).replace("/", "-")
    return f"r2d-test-{slug}:{ref}"


TestResult = namedtuple(
    "TestResult",
    (
        "repo",
        "ref",
        "resolved_ref",
        "kind",
        "test_id",
        "success",
        "path",
        "timestamp",
        "run_id",
        "repo2docker_version",
    ),
)


def test_one_repo(repo, ref="master", run_dir="./runs", force_build=False):
    repo_run_dir = os.path.join(run_dir, repo_slug(repo))
    log_dir = os.path.join(repo_run_dir, "logs")
    result_dir = os.path.join(repo_run_dir, "results")
    for d in [log_dir, result_dir]:
        try:
            os.makedirs(d)
        except FileExistsError:
            pass
    result_file = os.path.join(result_dir, f"results-{ref}-{run_id}.json")
    build_log_file = os.path.join(log_dir, f"build-{ref}-{run_id}.txt")

    checkout_path, resolved_ref = clone_repo(repo, ref)

    log.info(f"Building {repo}@{ref} in {repo_run_dir} with run id {run_id}")
    results = []

    def add_result(kind, test_id, success, path):
        path = os.path.relpath(path, run_dir)
        log.info(
            f"Recording test result: repo={repo}, kind={kind}, test_id={test_id}, {'success' if success else 'failure'}"
        )
        results.append(
            TestResult(
                repo,
                ref,
                resolved_ref,
                kind,
                test_id,
                success,
                path,
                timestamp,
                run_id,
                repo2docker.__version__,
            )
        )
        with open(result_file, "w") as f:
            json.dump(results, f, indent=1)

    try:
        image, checkout_path = build_repo(
            repo,
            resolved_ref=resolved_ref,
            checkout_path=checkout_path,
            build_log_file=build_log_file,
            force_build=force_build,
        )
    except Exception:
        # record build failure
        add_result(kind="build", test_id="build", success=False, path=build_log_file)
        return result_file, results
    else:
        add_result(kind="build", test_id="build", success=True, path=build_log_file)

    for result in run_tests(image, checkout_path, repo_run_dir):
        add_result(**result)

    return result_file, results


def print_summary(results, result_file):
    """Print a summary of th
    """
    build_result = results[0]
    print(
        f"Result summary for {build_result.repo}@{build_result.ref}-{build_result.resolved_ref}:"
    )
    print(f"  Result file: {result_file}")
    if not build_result.success:
        print(f"Build failed, see {build_result.path} for details")
        return

    if len(results) == 1:
        print("  No tests found!")
        return

    counters = defaultdict(int)
    failures = []
    for result in results[1:]:
        key = f"{result.kind}:{'ok' if result.success else 'fail'}"
        counters[key] += 1
        if not result.success:
            failures.append(result)
    print("  test:status: count")
    for key, count in sorted(counters.items()):
        print(f"  {key}: {count}")
    if failures:
        print(f"  {len(failures)} failures:")
        for r in failures:
            print(f"    {r.kind} {r.test_id}: {r.path}")
    else:
        print("OK!")


def main(argv=None):
    tornado.log.enable_pretty_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=str,
        default="./runs",
        help="directory in which to store results",
    )
    parser.add_argument(
        "--force-build",
        action="store_true",
        help="Force rebuild of images, even if an image already exists",
    )
    parser.add_argument("repos", nargs="+", help="repos to test")
    opts = parser.parse_args(argv)

    for repo in opts.repos:
        if "://" not in repo:
            # allow a/b shortcuts for github
            repo = "https://github.com/" + repo

        if "@" in repo:
            repo, ref = repo.split("@")
        else:
            ref = "master"
        try:
            result_file, results = test_one_repo(
                repo, ref=ref, run_dir=opts.run_dir, force_build=opts.force_build
            )
        except Exception:
            log.exception(f"Error testing {repo}@{ref}")
        else:
            print_summary(results, result_file)


if __name__ == "__main__":
    main()
