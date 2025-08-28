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
        self.x_root_d_client = XRootDClient(Config.config.backup.target_url)

    async def run_task(self) -> None:
        """
        Update the current pending_directory to the next timestamp for the task.
        Logs the current disk usage.
        Creates a CopyProcess for all files in the last pending directory.
        """
        cache_directory = Config.config.backup.cache_directory
        log.info("Starting backup for files in %s", cache_directory)

        total, used, free = shutil.disk_usage(cache_directory)
        percentage_used = 100 * used / total
        if percentage_used < Config.config.backup.warning_mark_percent:
            log.info("Current cache usage %.1f", percentage_used)
        else:
            log.warning("Current cache usage %.1f", percentage_used)

        try:
            self.x_root_d_client.backup(cache_directory)
        except Exception:  # Catch all exceptions to keep the Runner alive
            log.exception("Backup failed")
