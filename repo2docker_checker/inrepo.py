#!/usr/bin/env python3
"""Commands to run within a repo2docker image

Runs a single test
"""
import argparse
import importlib
import logging
import os
import tempfile

import tornado.log

log = logging.getLogger(__name__)


def import_test(modname):
    """Run an import test

    Just check if it imports!
    """
    log.info(f"Testing import of {modname}")
    importlib.import_module(modname)


def run_notebook(nb_path, output_dir):
    """Run a notebook tests

    executes the notebook and stores the output in a file
    """

    import nbformat
    from jupyter_client.kernelspec import KernelSpecManager
    from nbconvert.preprocessors.execute import executenb

    log.info(f"Testing notebook {nb_path}")
    with open(nb_path) as f:
        nb = nbformat.read(f, as_version=4)

    kernel_specs = KernelSpecManager().get_all_specs()
    kernel_info = nb.metadata.get("kernelspec") or {}
    kernel_name = kernel_info.get("name", "")
    kernel_language = kernel_info.get("language") or ""
    if kernel_name in kernel_specs:
        log.info(f"Found kernel {kernel_name}")
    elif kernel_language:
        log.warning(
            f"No such kernel {kernel_name}, falling back on kernel language={kernel_language}"
        )
        kernel_language = kernel_language.lower()
        # no exact name match, re-implement js notebook fallback,
        # using kernel language instead
        # nbconvert does not implement this, but it should
        for kernel_spec_name, kernel_info in kernel_specs.items():
            if (
                kernel_info.get("spec", {}).get("language", "").lower()
                == kernel_language
            ):
                log.warning(
                    f"Using kernel {kernel_spec_name} to provide language: {kernel_language}"
                )
                kernel_name = kernel_spec_name
                break
        else:
            log.warning(
                "Found no matching kernel for name={kernel_name}, language={kernel_language}"
            )
            summary_specs = [
                f"name={name}, language={info['spec'].get('language')}"
                for name, info in kernel_specs.items()
            ]
            log.warning(f"Found kernel specs: {'; '.join(summary_specs)}")

    exported = executenb(
        nb, cwd=os.path.dirname(nb_path), kernel_name=kernel_name, timeout=600
    )
    rel_path = os.path.relpath(nb_path, os.getcwd())
    dest_path = os.path.join(output_dir, "notebooks", rel_path)
    log.info(f"Saving exported notebook to {dest_path}")
    try:
        os.makedirs(os.path.dirname(dest_path))
    except FileExistsError:
        pass

    with open(dest_path, "w") as f:
        nbformat.write(exported, f)


test_functions = {
    "import": import_test,
    "notebook": run_notebook,
}


def main():
    tornado.log.enable_pretty_logging()
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=str,
        default=tempfile.gettempdir(),
        help="Directory to store test results",
    )
    parser.add_argument("test_type", choices=sorted(test_functions))
    parser.add_argument("test", type=str)
    opts = parser.parse_args()
    test_f = test_functions[opts.test_type]
    test_f(opts.test, opts.output_dir)


if __name__ == "__main__":
    main()
