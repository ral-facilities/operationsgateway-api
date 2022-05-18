# OperationsGateway API
This is an API built using FastAPI to work with MongoDB and the data stored as part of the OperationsGateway project.


## Environment Setup
[Poetry](https://python-poetry.org/) is used to manage the dependencies of this API. To install Poetry, follow [the instructions](https://python-poetry.org/docs/master/#installing-with-the-official-installer) from their documentation.

To install the project's dependencies, execute `poetry install`. The dependencies and the code in this repo are compatible with Python 3.6+.

## Nox Sessions
Like DataGateway API, this repository contains a Nox file (`noxfile.py`) which exists in the root level of this repository. There are a handful of sessions which help with repetitive tasks during development To install Nox, use the following command:

```bash
pip install --user --upgrade nox
```

To run a specific Nox session, use the following:

```bash
nox -s [SESSION NAME]
```

Currently, the following Nox sessions have been created:
- `black` - this uses [Black](https://black.readthedocs.io/en/stable/) to format Python code to a pre-defined style.
- `lint` - this uses [flake8](https://flake8.pycqa.org/en/latest/) with a number of additional plugins (see the included `noxfile.py` to see which plugins are used) to lint the code to keep it Pythonic. `.flake8` configures `flake8` and the plugins.
- `safety` - this uses [safety](https://github.com/pyupio/safety) to check the dependencies (pulled directly from Poetry) for any known vulnerabilities. This session gives the output in a full ASCII style report.
- `tests` - this uses [pytest](https://docs.pytest.org/en/stable/) to execute the automated tests in `test/`. There are currently no automated tests written for this repository however.

## API Configuration
In `operationsgateway_api/`, there is an example config file (`config.yml.example`). Copy this example so `config.yml` exists in the same directory level and edit the configuration as needed for your system.

## API Startup
To start the API, use the following command:

```bash
poetry run python -m operationsgateway_api.src.main
```

Assuming default configuration, the API will exist on 127.0.0.1:8000. You can visit `/docs` in a browser which will give an OpenAPI interface detailing each of the endpoints and an option to send requests to them. Alternatively, you can send requests to the API using a platform such as Postman to construct and save specific requests.
