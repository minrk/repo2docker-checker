import os

import pytest

import inrepo


def test_import_fails():
    with pytest.raises(ImportError):
        inrepo.import_test("nosuchmod")


def test_import_ok():
    inrepo.import_test("sys")


def test_notebook_fails(tmpdir, here):
    output_dir = str(tmpdir.mkdir("out"))
    nb = os.path.join(here, "fails.ipynb")
    with pytest.raises(Exception):
        inrepo.run_notebook(nb, output_dir)


def test_notebook_ok(tmpdir, here):
    output_dir = str(tmpdir.mkdir("out"))
    nb = os.path.join(here, "passes.ipynb")
    inrepo.run_notebook(nb, output_dir)
    assert os.listdir(output_dir)
