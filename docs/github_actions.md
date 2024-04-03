# GitHub Actions

For our CI, we use GitHub Actions. There are multiple jobs which run the tests in multiple versions of Python (running an ingestion script beforehand to load data for the tests) and perform code formatting/linting on the codebase etc. The steps are fairly self-explanatory, but there are a few things worth noting that may not be immediately obvious.

## Ubuntu 20.04 & 22.04
The Python tests are across a variety of Python versions, some using Ubuntu 20.04 runners and others using Ubuntu 22.04. This is because the build dependencies for python-ldap (installed using `apt-get`) are specific to Python versions and the newer versions aren't available in Ubuntu 20.04. The solution to this is running tests across all desired Python versions and across both OSs, but disabling one of the operating systems from running on each version of Python. 22.04 is disabled on 3.8 & 3.9, 20.04 is disabled on 3.10 & 3.11.

## Extra Steps to Install mongoimport on 22.04 Runners
A consequence of using Ubuntu 22.04 is the loss of command line tools from MongoDB from the runners' default environment. This is important as our scripts for ingesting test data into the API use `mongoimport` to import data stored in JSON files. To workaround this, the CI contains a step that runs on 22.04 which executes a series of `apt` commands to install these tools. The [pull request](https://github.com/ral-facilities/operationsgateway-api/pull/97) that made these changes provide a couple of references to discussions on other GitHub repos.

## Minio as S3 Storage
The CI used to use Echo to store data for the tests. However, this was determined to be too slow, with the ingestion script taking multiple hours to complete, sometimes completing unsuccessfully. It appeared that some kind of rate limiting from GitHub Actions was taking place - when interacting with Echo, idling of ~60 seconds at a time would frequently occur.

To combat this issue, the CI now sets up a local instance of `minio` using a Docker container which the API connects to when it's launched in the ingestion script. Minio is a way of having S3 storage locally, mimicking AWS (and therefore Echo S3).

## Caching
To speed up the workflows, caching is used to store Python dependencies and load them into the virtual environments. This is done for both Pip and poetry - loading the `pip` cache helps speed up the installation of Poetry and Nox and the `poetry` cache helps with the project dependencies. The caching is done in a fairly standard way, but the cache key includes something that keys from other repos might not include, `env.pythonLocation`.

An issue was noticed when merging a pull request - tests on Python 3.9 & 3.10 failed on `main`, but had previously passed on the branch used for the PR. This was because the virtual environments for the Nox sessions of the tests was broken - `python` couldn't be found, causing the `pytest` command to not be found. After some investigation, it was noticed that the Python versions used was slightly different, specifically the patch versions. Someone has encountered a similar issue in the past (see [#735 on the Nox repo](https://github.com/wntrblm/nox/issues/735)).

The problem was caused by the caching. The caches were created using a different patch version of Python (e.g. 3.10.13), but a slightly newer version was being used on that Actions run (e.g. 3.10.14). This can happen because the default Python versions on the runners can change as the images are updated. This happened with Ubuntu 22.04 in this case - [this PR](https://github.com/actions/runner-images/pull/9560) shows that Python 3.9 & 3.10 had patch version updates, causing this problem. Unless a patch version is specified, `setup-python` uses the default versions on the runner images.

A fix has been applied to the cache key, as suggested [in this issue comment](https://github.com/wntrblm/nox/issues/735#issuecomment-1854599576). `env.pythonLocation` has been added to the key because this includes the patch version of the Python version being used. This means that different caches will be used for 3.10.13 and 3.10.14, preventing this issue from occuring in the future.
