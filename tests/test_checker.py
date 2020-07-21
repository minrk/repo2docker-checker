import pytest

from repo2docker_checker.checker import build_repo
from repo2docker_checker.checker import clone_repo
from repo2docker_checker.checker import find_notebooks
from repo2docker_checker.checker import main

example_repo_short = "binder-examples/requirements"
example_repo = f"https://github.com/{example_repo_short}"
example_ref_passes = "11cdea057c300242a30e5c265d8dc79f60f644e1"
example_ref_fails = "d37d5723fb410dbfb7fa3f470ac8bc211c5e6718"


def test_build_succeeds(tmpdir):
    repo = example_repo
    ref = example_ref_passes
    build_log_file = tmpdir.join("build-log.txt")
    checkout_path, resolved_ref, timestamp = clone_repo(repo, ref)
    assert ref.startswith(resolved_ref)
    image_id, checkout_path = build_repo(
        repo, resolved_ref, checkout_path, str(build_log_file), force_build=True
    )
    assert build_log_file.exists()
    with build_log_file.open() as f:
        assert "Successfully tagged" in f.read()

    # second build should be skipped
    build_log_file = tmpdir.join("build-log-reuse.txt")
    image_id, checkout_path = build_repo(
        repo, resolved_ref, checkout_path, str(build_log_file), force_build=False
    )
    with build_log_file.open() as f:
        assert "already built" in f.read()

    # force should trigger rebuild
    build_log_file = tmpdir.join("build-log-force.txt")
    image_id, checkout_path = build_repo(
        repo, resolved_ref, checkout_path, str(build_log_file), force_build=True
    )
    with build_log_file.open() as f:
        assert "Successfully tagged" in f.read()


def test_build_fails(tmpdir):
    repo = "https://github.com/minrk/repo2docker-checker"
    ref = "build-fails"
    build_log_file = tmpdir.join("build-log.txt")
    checkout_path, resolved_ref, timestamp = clone_repo(repo, ref)
    assert resolved_ref.startswith("a68ea7")
    assert timestamp == "2020-07-01T14:23:17+02:00"
    with pytest.raises(Exception):
        image_id, checkout_path = build_repo(
            repo, resolved_ref, checkout_path, str(build_log_file)
        )
    assert build_log_file.exists()
    with build_log_file.open() as f:
        assert "No matching distribution" in f.read()


def test_example_passes():
    main([f"{example_repo}@{example_ref_passes}"])


def test_example_fails():
    main([f"{example_repo_short}@{example_ref_fails}"])


def test_find_notebooks(tmpdir):
    repo = tmpdir.mkdir("repo")
    checkpoints = repo.mkdir(".ipynb_checkpoints")
    subdir = repo.mkdir("subdir")
    nb1 = repo.join("a.ipynb")
    nb2 = subdir.join("b.ipynb")
    txt = subdir.join("a.txt")
    cp = checkpoints.join("c.ipynb")
    for f in (txt, nb1, nb2, cp):
        with f.open("w") as _:
            pass

    notebooks = sorted(find_notebooks(str(repo)))
    assert notebooks == [path.relto(repo) for path in (nb1, nb2)]
