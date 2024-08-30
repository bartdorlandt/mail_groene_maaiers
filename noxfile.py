"""noxfile."""
from nox import session
import nox

nox.options.default_venv_backend = "uv"


@session()
def tests(session):
    session.install(".",)
    session.install("pytest", "pytest-cov")
    session.run("pytest")


@session()
def lint(session):
    session.install("ruff")
    session.run("ruff", "check", ".")


@session()
def typing(session):
    session.install("mypy")
    session.run("mypy", ".", "--junit-xml", "mypy_report.xml")
