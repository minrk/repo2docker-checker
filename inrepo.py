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
    from nbconvert.preprocessors.execute import executenb

    log.info(f"Testing notebook {nb_path}")
    with open(nb_path) as f:
        nb = nbformat.read(f, as_version=4)
    exported = executenb(nb, cwd=os.path.dirname(nb_path))
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
