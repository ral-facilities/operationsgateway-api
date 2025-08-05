import logging
import os

from XRootD.client import URL
from XRootD.client.responses import XRootDStatus
from XRootD.client.utils import CopyProgressHandler


log = logging.getLogger()


class XRootDProgressHandler(CopyProgressHandler):
    """
    Subclass to handle logging and cleanup of XRootD copy jobs.
    """

    jobs = {}

    def begin(
        self,
        jobId: int,  # noqa: N803
        total: int,
        source: URL,
        target: URL,
    ) -> None:
        """
        Called on the start of each job. Caches the source against jobId so that we can
        remove the source file when the job completes.
        """
        log.debug("Starting job %s of %s: %s", jobId, total, source)
        self.jobs[jobId] = source.path

    def end(self, jobId: int, results: XRootDStatus) -> None:  # noqa: N803
        """
        Called on the end of each job. Uses the cached source to clean up the local
        cache iff the job was successful.
        """
        if results.ok:
            log.debug("Copy successful, removing source file")
            os.remove(self.jobs[jobId])
        else:
            log.error("Copy failed with code %s: %s", results.code, results.message)

    def update(self, jobId: int, processed: int, total: int) -> None:  # noqa: N803
        """
        Called with the current number of bytes transferred for the job.
        """
        msg = "Update on job %s: %s of %s bytes transferred"
        log.debug(msg, jobId, processed, total)
