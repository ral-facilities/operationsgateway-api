import logging
import shutil

from operationsgateway_api.src.backup.x_root_d_client import XRootDClient
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.runner_abc import RunnerABC

log = logging.getLogger()


class XRootDCopyRunner(RunnerABC):
    """
    Controls the (optional) task to periodically copy files from a local source to the
    configured XRootD backup server.
    """

    def __init__(self) -> None:
        super().__init__(
            task_name="XRootD Copy",
            cron_string=Config.config.backup.copy_cron_string,
            timezone_str=Config.config.backup.timezone_str,
        )
        self.set_pending_directory()

    async def run_task(self) -> None:
        """
        Update the current pending_directory to the next timestamp for the task.
        Logs the current disk usage.
        Creates a CopyProcess for all files in the last pending directory.
        """
        current_directory = self.pending_directory
        log.info("Starting backup for files in %s", current_directory)
        self.set_pending_directory()

        total, used, free = shutil.disk_usage(Config.config.backup.cache_directory)
        percentage_used = 100 * used / total
        if percentage_used < Config.config.backup.warning_mark_percent:
            log.info("Current cache usage %.1f", percentage_used)
        else:
            log.warning("Current cache usage %.1f", percentage_used)

        XRootDClient.backup(current_directory)

    def set_pending_directory(self) -> None:
        """
        Updates the current pending_directory, where incoming files will be written to.
        Note that this does not take the next entry from runner_dates. This is handled
        by start_thread on the super class.
        """
        next_date = self.get_next_run_task_date().isoformat()
        self.pending_directory = Config.config.backup.cache_directory / next_date
