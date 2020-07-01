import os
import sys

import pytest

here = os.path.abspath(os.path.dirname(__file__))
repo = os.path.abspath(os.path.join(here, os.pardir))
sys.path.insert(0, repo)

import inrepo


def test_import_fails():
    with pytest.raises(ImportError):
        inrepo.import_test("nosuchmod")


def test_import_ok():
    inrepo.import_test("sys")


def test_notebook_fails(tmpdir):
    output_dir = str(tmpdir.mkdir("out"))
    nb = os.path.join(here, "fails.ipynb")
    with pytest.raises(Exception):
        inrepo.run_notebook(nb, output_dir)


def test_notebook_ok(tmpdir):
    output_dir = str(tmpdir.mkdir("out"))
    nb = os.path.join(here, "passes.ipynb")
    inrepo.run_notebook(nb, output_dir)
    assert os.listdir(output_dir)
