# MongoDB

## 5.0 to 7.0
These instructions allow developers to move from MongoDB 5.0 to 7.0 to match the database provided by Database Services. As re-ingestion only takes a few minutes, completely wiping the machine of 5.0 and doing a clean install for 7.0 seems like an easier alterative than upgrading from 5.0 to 6.0 and then 6.0 to 7.0. These commands have been tested on a Rocky 8 VM but should work on Rocky 9 providing the small edit is made to the Yum repo

```bash
# Stop MongoDB process
sudo systemctl stop mongod
# Uninstall packages using yum
sudo yum erase mongodb-*
# Check that everything's been uninstalled
yum list installed | grep -i mongod
# Remove data directories, databases, logs
sudo rm -rf /var/log/mongodb /var/lib/mongo*
# Disable yum repo for MongoDB 5.0
sudo yum-config-manager --disable mongodb-org-5.0

# Add yum repo for MongoDB 7.0
sudo touch /etc/yum.repos.d/mongodb-org-7.0.repo
```
Paste the following into /etc/yum.repos.d/mongodb-org-7.0.repo (edit the /8/ to /9/ if you're using Rocky 9):

```ini
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/8/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://pgp.mongodb.com/server-7.0.asc
```
```bash
# Install the latest stable version of MongoDB
sudo yum install mongodb-org
# Start MongoDB, enter the shell and check the "Using MongoDB:" line lists a version 7.x.x
sudo systemctl start mongod
mongosh
```

Once MongoDB uses 7.0, you can re-ingest the data (using `ingest_echo_data.py`) as per `test_data.md`.
