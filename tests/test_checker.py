import repo2docker_checker


def test_example_passes():
    repo2docker_checker.main(["binder-examples/requirements"])


def test_example_fails():
    repo2docker_checker.main(
        ["binder-examples/requirements@d37d5723fb410dbfb7fa3f470ac8bc211c5e6718"]
    )
