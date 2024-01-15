[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Build Status](https://github.com/ral-facilities/operationsgateway-api/workflows/CI/badge.svg?branch=main)](https://github.com/ral-facilities/operationsgateway-api/actions?query=workflow%3A%22CI%22)
[![Codecov](https://codecov.io/gh/ral-facilities/operationsgateway-api/branch/main/graph/badge.svg)](https://codecov.io/gh/ral-facilities/operationsgateway-api)


# OperationsGateway API
This is an API built using [FastAPI](https://fastapi.tiangolo.com/) to work with [MongoDB](https://www.mongodb.com/) and the data stored as part of the OperationsGateway project.


## Environment Setup
[Poetry](https://python-poetry.org/) is used to manage the dependencies of this API. To install Poetry, follow [the instructions](https://python-poetry.org/docs/master/#installing-with-the-official-installer) from their documentation.

To install the project's dependencies, execute `poetry install`. The dependencies and the code in this repo are compatible with Python 3.8+.

## Nox Sessions
Like [DataGateway API](https://github.com/ral-facilities/datagateway-api), this repository contains a [Nox](https://nox.thea.codes) file (`noxfile.py`) which exists in the root level of this repository. There are a handful of sessions which help with repetitive tasks during development To install Nox, use the following command:

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
In `operationsgateway_api/`, there is an example config file (`config.yml.example`). Copy this example so `config.yml` exists in the same directory level and edit the configuration as needed for your system. There is also a logging configuration file (`logging.ini.example`). Follow the same procedure as the config file as to set up the logging.

## Authentication Configuration

The authentication system uses JSON Web Tokens (JWTs) which require a private and public key pair to encrypt and decrypt the tokens. The keys can be generated by navigating to a directory and typing the command:

```bash
ssh-keygen -b 2048 -t rsa
```

Enter the path for the file as `id_rsa` to create the keys in the current directory rather than in your home directory.

Press enter twice when prompted for the password so as not to set one.

The key should be OpenSSH encoded - this format is generated by default in Rocky 8. You can check whether your key is in the correct format by checking the start of the private key; it should be `-----BEGIN OPENSSH PRIVATE KEY-----`.

Then edit the ```private_key_path``` and ```public_key_path``` settings in the ```auth``` section of the ```config.yml``` file to reflect the location where these keys have been created.

### Adding User Accounts

The authentication system requires any users of the system to have an account set up in the database. Two types of user login are currently supported: federal ID logins for "real" users, and "local" logins for functional accounts.

To add some test accounts to the system, use the user data stored in `util/users_for_mongoimport.json`. Use the following command to import those users into the database:

```bash
mongoimport --db='opsgateway' --collection='users' --mode='upsert' --file='util/users_for_mongoimport.json'
```

Using the `upsert` mode allows you to update existing users with any changes that are made (e.g. added an authorised route to their entry) and any new users are inserted as normal. The command's output states the number of documents that have been added and how many have been updated.

## Image Storage
Configuration for image storage is stored in the `images` section of the config file. Images are stored using S3 object storage, currently the STFC Echo instance. Lots of documentation online references the AWS offering, but as S3 is the underlying storage technique, we can interact with Echo in the same way that a user would interact with AWS S3.

Credentials to connect to Echo are provided in `config.yml`, as well as a bucket name, which is the location on S3 storage where images will be stored.

For the API, we have multiple buckets, used for different purposes. For example, there's a bucket used for the dev server, a bucket per developer for their development environment, as well as buckets that are created for a short period of time for specific testing. This ensures that we're not overwriting each other's data and causing issues. For GitHub Actions, each run will create a new bucket, ingest data for testing and delete the bucket at the end of the run.

To manage buckets, [s4cmd](https://github.com/bloomreach/s4cmd) is a good command line utility. It provides an Unix-like interface to S3 storage, based off of `s3cmd` but has higher performance when interacting with large files. It is a development dependency for this repository but can also be installed using `pip`. There's an example configuration file in `.github/ci_s3cfg` which can be placed in `~/.s3cfg` and used for your own development environment.

Here's a few useful example commands (the [s4cmd README](https://github.com/bloomreach/s4cmd/blob/master/README.md) provides useful information about all available commands):
```bash
# To make calling `s4cmd` easier when installed as a development dependency, I've added the following alias to `~/.bashrc`
# Change the path to the Poetry virtualenv as needed
alias s4cmd='/root/.cache/pypoetry/virtualenvs/operationsgateway-api-pfN98gKB-py3.8/bin/s4cmd --endpoint-url https://s3.echo.stfc.ac.uk'

# The following commands assume the alias has been made
# Create a bucket called 'og-my-test-bucket' on STFC's Echo S3
s4cmd mb s3://og-my-test-bucket

# List everything that the current user can see
s4cmd ls

# List everything inside 'og-my-test-bucket'
s4cmd ls s3://og-my-test-bucket

# Remove all objects in bucket
s4cmd del --recursive s3://og-my-test-bucket
```

## API Startup
To start the API, use the following command:

```bash
poetry run python -m operationsgateway_api.src.main
```

Assuming default configuration, the API will exist on 127.0.0.1:8000. You can visit `/docs` in a browser which will give an OpenAPI interface detailing each of the endpoints and an option to send requests to them. Alternatively, you can send requests to the API using a platform such as Postman to construct and save specific requests.
