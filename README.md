# repo2docker-checker

Sampling repositories built with repo2docker.


Install:

    pip install git+https://github.com/minrk/repo2docker-checker

Check a repo:

    repo2docker-checker binder-examples/requirements


Our goal is to make some scripts to check:

- does it build?
- is there something to run?
- does it run?
- ...why?

Currently, the output for each run is stored in a csv in `repo/results/results-...csv`.

For now, we only have notebooks as tests, run with `nbconvert --execute` (the Python equivalent, anyway).

Each test row consists of:

- a test 'kind' (build or notebook),
- boolean 'success',
- a path relative to the run directory containing a log file for details (mostly interesting for failures).
- additional metadata such as the repo, ref, commit date, repo2docker version, etc.

This is a work in progress, summer research project at Simula Research Laboratory with @Vildeeide.
