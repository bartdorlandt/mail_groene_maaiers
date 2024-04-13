"""noxfile."""
from nox_poetry import session as nox_session

py_versions = ["3.10", "3.11", "3.12"]


@nox_session(python=py_versions)
def tests(session):
    session.install("pytest", "pytest-cov")
    session.run_always("poetry", "install", external=True)
    session.run("pytest")


@nox_session(python=py_versions[0])
def lint(session):
    session.install("ruff")
    session.run("ruff", "check", ".")


@nox_session(python=py_versions[0])
def typing(session):
    session.install("mypy")
    session.run("mypy", ".", "--junit-xml", "mypy_report.xml")
