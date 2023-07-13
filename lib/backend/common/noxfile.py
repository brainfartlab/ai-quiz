import nox
from nox_poetry import session


nox.options.sessions = "lint", "tests"


@session(python=["3.10"])
def tests(session):
    #session.install(".", "pytest", poetry_groups=["dev"])
    session.install("pytest", "pytest-cov", "coverage[toml]", "pytest-env", "boto3", ".")
    session.run("pytest", "--cov")


@session(python=["3.10"])
def lint(session):
    #session.install(".", "pytest", poetry_groups=["lint"])
    session.install("flake8", "flake8-black", "flake8-import-order")
    session.run("flake8", "common", "tests")


@session(python=["3.10"])
def black(session):
    session.install("black")
    session.run("black", "common", "tests")
