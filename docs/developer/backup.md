# Backup

While it is not yet confirmed, we are expecting that data will be available via OperationsGateway for 3 years in line with EPAC's data policy. During this time, it should be in online storage (available to read on request). After the retention period, the data can be deleted from online storage. However there is a chance that in exceptional circumstances they will want to access data which is more than 3 years old.

Alongside this, there is also the possibility of disaster, and the loss of the data in online storage. To mitigate this, it would also be desirable to have a second copy of all data from the earliest possibility which could then be used for disaster recovery.

To meet both these requirements, the facilities tape allocation can be used. Tape is the most cost effective long term offline storage the department can offer. In the context of facilities data (PBs per year), the data rates and volumes expected for OperationsGateway are low and the usage pattern minimal (only restoring fir disaster recovery). Therefore a relatively light solution can be implemented without the need for additional services such as StorageD (to aggregate data) or FTS (to mediate transfers).

## Ingest process

Transfers to and from tape will use the [XRootD](https://xrootd.org/) framework. The XRootD copy process copies data from a source to a target "storage endpoint". These can be local storage or XRootD server(s). This prevents us from using Echo as the source (without first copying the data to local storage, which would result in more transfers than strictly necessary).

In principle either the record (hdf5) files or channel (png, npz, json) files could be copied. Due to how tape storage marks files, it is more performant to store fewer large files than many small ones. This makes one hdf5 file of around 200MB a more tape friendly option than 100s of files around or smaller than 1MB (though once again the relatively small data rates mean that we are not likely to be limited by the effects of file size).

When a file is ingested, we have those bytes in memory. Writing these to the configured local cache directory introduces minimal (< 10 ms) overhead to the ingest request (which can take minutes due to the relatively slow communication with Echo). The actual copy to tape may be slower, and a problem there should not cause ingest to fail. Therefore all we do during ingest is write the bytes, with the copy to tape taking place in a later, decoupled process.

## Copy to tape

Following the existing design pattern for the `scheduler_runner`, a new runner using the FastAPI lifespan function has been added. This checks and logs the current usage of the configured cache directory, then starts the backup process. This walks through the cache directory, and for each file either:
- Removes the local file if there is already a copy registered, depending on the value of the config setting `auto_remove`
- Adds it to an XRootD `CopyProcess`

These files are copied to the disk buffer of the XRootD server. This copy should be relatively quick, however the process of writing them from this buffer to tape can be prolonged. It depends on several factors, including the amount of time since the last write, the number of files in the buffer, whether any other tapes are mounted etc. If having a copy in the buffer is deemed acceptable (and `auto_remove` set to `"cached"`), then the local copy will be removed as soon as the copy into XRootD's buffer cache is complete. Otherwise deletion may occur at the next runner execution.

The logic for handling the calls to XRootD is all contained within the `xrootd-utils` package, and if further modifications are required then it should be updated as needed.

## Notifications and logging

The `xrootd-utils` package, like `operationsgateway-api`, uses the standard python `logging` library. This will log whenever one of the underlying XRootD commands fails, as well as updates on the progress of the copy at INFO and DEBUG levels.
