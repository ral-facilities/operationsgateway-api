# Dev Server
The dev server is a Rocky 8 VM hosted by RIG that allows us to deploy the API for the frontend to use for their development. It's a shared resource so care should be taken to ensure disruption is communicated and when the API has been re-deployed, all developers are made aware of the changes to that instance of the API.

## Deploying API to Dev Server
Deploying the API is done using [OperationsGateway Ansible](https://github.com/ral-facilities/operationsgateway-ansible). That repo contains a README but before deploying, there's a couple of things to ask yourself to minimise the chance of a mistaken deployment:
- Are you deploying to the correct host?
- Is the commit hash of the API correct? Check `operationsgateway_api_version`
- Do the templating files for the config need updating? This can be easy to miss if a config option has been added to the API that you forgot about
- Are the cron jobs for the simulated data disabled? If the `simulated-data` role is being run when you deploy, they might get re-enabled and this may not be your intention

### Finding Commit Hash of Current Deployment
To ensure the frontend team get access to new functionality of the API in a reasonable timeframe (so they aren't blocked), deployments can take place before functionality has gone through code review and merged into the main branch. Where multiple pieces of functionality are awaiting code review, this can mean merging multiple branches together; keeping track of exactly what's been deployed can sometimes be confusing. 

When deploying with Ansible, you must specify the commit hash of the API to install which can be found in the following file:
```bash
# If this exact path doesn't exist, check Ansible to find where the API is being installed (look for the operationsgateway_api_virtualenv variable)
/opt/operationsgateway-api/lib/python3.8/site-packages/operationsgateway_api-0.1.0.dist-info/direct_url.json
>>> {"url": "ssh://git@github.com/ral-facilities/operationsgateway-api.git", "vcs_info": {"commit_id": "90701efdc7c5565e4d0afa80b9b7e1c81418f2d7", "requested_revision": "90701efdc7c5565e4d0afa80b9b7e1c81418f2d7", "vcs": "git"}
```

To view that commit, you can go to GitHub and insert the commit hash into the following URL: https://github.com/ral-facilities/operationsgateway-api/commit/[COMMIT-HASH]

## Systemd
To control the API on the dev server, a `systemd` service is added to the machine by Ansible. This allows you to do all the typical things you'd be able to do with a systemd service (i.e. start/stop/restart) and you can check on the logs using `journalctl -u og-api`.

## Apache/Certificates
The API is exposed to the outside world using a reverse proxy; the API lives on port 8000 but port 443 is used to access it. If a user accesses the API using port 80, it'll forward on their request to port 443. This works fine for GET requests but unusual things can happen for other request types (e.g. POST), particularly requests which contain a request body (see https://stackoverflow.com/a/21859641 for further information).

Certificates are requested through the DI Service Desk, where the normal process applies - generate a CSR, submit a ticket containing the CSR asking for the certificate to be generated and download the files once they've been generated. Alan's [certificate cheatsheet](https://github.com/ral-facilities/dseg-docs/blob/master/certs-cheat-sheet.md) is a great resource to easily generate a CSR if you're not familiar with that process.

When downloading the certificates, I click the following links: 
- `cert` - "as Certificate only, PEM encoded"
- `ca` (you need to remove the first certificate (our cert) from this file, so 2 remain) - "as Certificate (w/ issuer after), PEM encoded:"

The certificate files are stored in `/etc/httpd/certs/` and symlinks are applied to them which allows easy swapping of files. When changes are made, do a `systemctl restart httpd` to ensure any file/config changes take effect.

To open ports, use `firewall-cmd`; this is a Rocky 8 VM so this is different to older Centos 7 RIG VMs where `iptables` was used. To view current rules, use `firewall-cmd --list-all`. Ports 80 & 443 are opened when deployed using Ansible.

## Storage
The API is hooked up to a MongoDB database provided by Database Services containing simulated data as well as using Echo S3. Credentials for these resources are stored in the shared Keeper folder and a specific bucket is used for the dev server (`s3://og-dev-server`).

### Simulated Data
The dev server contains 12 months worth of simulated data (October 2022-October 2023) which is reproducible using HDF files stored in the `s3://OG-YEAR-OF-SIMULATED-DATA` bucket in Echo. There are cron jobs which control data generated each day, a test to mimic incoming load from EPAC in production. More detail about the inner workings of this mechanism can be found in `docs/epac_simulated_data.md`.

Due to storage constraints, the daily data mechanism is currently disabled (the cron jobs have been commented out) and a large number of waveforms have been removed from the database (March 2023 to December 2023 inclusive). The records data is still available for this period (including waveform thumbnails) but it's probably best not to click on the waveform thumbnails in the frontend for data in that timeframe as there's no longer any waveforms for them. Waveforms still exist for data in January 2024 (January 1st to January 4th). Images are unaffected as they're not stored in the database.

The period March 2023-October 2023 is data from the year of HDF files that were generated and stored on Echo. Once I've done the work to move waveforms out of the database, I'll re-ingest data from March 2023 - October 2023 to restore the waveforms for that period (and re-enable the cron jobs for daily data).

### Local Database for Gemini Data
Before using simulated EPAC data, we used a small amount of Gemini data, stored in a local database; it is equivalent to the databases used in our development environments - local DBs, no auth, named `opsgateway`. There may be cases where in the future, we need to switch back to the Gemini data as this may allow us to test something that isn't so easy to test with the simulated data. To do this, the following things will need to be done:
- Change the API config to point to the local database - both the URL and database name are different
- Point to a different Echo bucket - images were stored on disk when the Gemini data was last used so a new bucket should be created. The images used to be stored in `/epac_storage` but have since been deleted.
- Restart the API using `systemctl restart og-api`

An upcoming piece of work (as of Feb 2024) is to move waveforms to be stored in Echo (instead of the database). When this happens (and is deployed to the dev server), reingestion of the Gemini data might be required. Follow the instructions in `docs/test_data.md` for more info on this.
