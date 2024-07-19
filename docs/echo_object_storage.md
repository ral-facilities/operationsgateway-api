# Echo Object Storage
Waveforms and images are stored using S3 object storage (using the same bucket), currently the STFC Echo instance. Lots of documentation online references the AWS offering, but as S3 is the underlying storage technique, we can interact with Echo in the same way that a user would interact with AWS S3.

Configuration to connect with Echo is stored in the `echo` section of the config file - credentials are stored in Keeper. This section includes a bucket name, which is the location on S3 storage where images & waveforms will be stored. For the API, we have multiple buckets, used for different purposes. For example, there's a bucket used for the dev server, a bucket per developer for their development environment, as well as buckets that are created for a short period of time for specific testing. This ensures that we're not overwriting each other's data and causing issues. For GitHub Actions, each run will create a new bucket, ingest data for testing and delete the bucket at the end of the run.

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
