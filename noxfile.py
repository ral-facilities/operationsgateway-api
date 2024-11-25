import os
import tempfile

import nox
from nox.command import CommandFailed

# Separating Black away from the rest of the sessions
nox.options.sessions = "lint", "safety", "tests"
code_locations = "operationsgateway_api", "test", "noxfile.py", "util"


def install_with_constraints(session, *args, **kwargs):
    # Auto file deletion is turned off to prevent a PermissionError experienced on
    # Windows
    with tempfile.NamedTemporaryFile(delete=False) as requirements:
        session.run(
            "poetry",
            "export",
            "--dev",
            "--format=requirements.txt",
            "--without-hashes",
            f"--output={requirements.name}",
            external=True,
        )
        # Using sed to remove extras from the constraints file, thereby fixing the
        # error "Constraints cannot have extras". A better solution might be to
        # use `poetry install --only dev` but this requires a newer version of
        # Poetry than we're using in our development environments. See
        # https://github.com/jazzband/pip-tools/issues/1300#issuecomment-818122483
        # for more info relating to the sed solution
        sed_expression = r"s/\[.*\]//g"
        try:
            session.run("sed", "-i", sed_expression, requirements.name, external=True)
        except CommandFailed:
            # Try running the Mac version of the command
            session.run(
                "sed",
                "-i",
                "",
                sed_expression,
                requirements.name,
                external=True,
            )

        session.install(f"--constraint={requirements.name}", *args, **kwargs)

        try:
            # Due to delete=False, the file must be deleted manually
            requirements.close()
            os.unlink(requirements.name)
        except IOError:
            session.log("Error: The temporary requirements file could not be closed")


@nox.session(reuse_venv=True)
def black(session):
    args = session.posargs
    install_with_constraints(session, "black")
    session.run("black", *code_locations, *args, external=True)


@nox.session(reuse_venv=True)
def lint(session):
    args = session.posargs or code_locations
    install_with_constraints(
        session,
        "flake8",
        "flake8-black",
        "flake8-broken-line",
        "flake8-bugbear",
        "flake8-builtins",
        "flake8-commas",
        "flake8-comprehensions",
        "flake8-import-order",
        "flake8-logging-format",
        "pep8-naming",
    )
    session.run("flake8", *args)


@nox.session(reuse_venv=True)
def safety(session):
    install_with_constraints(session, "safety")
    with tempfile.NamedTemporaryFile(delete=False) as requirements:
        session.run(
            "poetry",
            "export",
            "--dev",
            "--format=requirements.txt",
            "--without-hashes",
            f"--output={requirements.name}",
            external=True,
        )
        session.run(
            "safety",
            "check",
            f"--file={requirements.name}",
            "--full-report",
            # jinja2 report widely disputed as not valid, no fix available:
            # https://github.com/pallets/jinja/issues/1994
            "--ignore",
            "70612",
        )

        try:
            # Due to delete=False, the file must be deleted manually
            requirements.close()
            os.unlink(requirements.name)
        except IOError:
            session.log("Error: The temporary requirements file could not be closed")


@nox.session(python=["3.11", "3.12", "3.13"], reuse_venv=True)
def tests(session):
    args = session.posargs
    session.run("poetry", "install", "--without", "simulated-data", external=True)
    session.run("pytest", *args)
