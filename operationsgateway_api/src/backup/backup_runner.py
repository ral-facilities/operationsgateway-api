import logging
import shutil
from smtplib import SMTP

from xrootd_utils.client import Client
from xrootd_utils.common import AutoRemove

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.runner_abc import RunnerABC

log = logging.getLogger()


class BackupRunner(RunnerABC):
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
        self.x_root_d_client = Client(Config.config.backup.target_url)

    async def run_task(self) -> None:
        """
        Update the current pending_directory to the next timestamp for the task.
        Logs the current disk usage.
        Creates a CopyProcess for all files in the last pending directory.
        """
        cache_directory = Config.config.backup.cache_directory
        log.info("Starting backup for files in %s", cache_directory)
        BackupRunner._check_cache_usage()

        try:
            results = self.x_root_d_client.backup(cache_directory, AutoRemove.BACKED_UP)
            if results["failed"]:
                log.warning(
                    "Backup completed: %s succeeded, %s failed, %s removed",
                    len(results["succeeded"]),
                    len(results["failed"]),
                    len(results["removed"]),
                )
                lines = [
                    (
                        f"Backup completed: {len(results['succeeded'])} succeeded, "
                        f"{len(results['failed'])} failed, "
                        f"{len(results['removed'])} removed"
                    ),
                    "",
                    "Failed paths were:",
                ]
                lines += results["failed"]
                BackupRunner._send_mail("Backup: transfer failures", lines)
            else:
                log.info(
                    "Backup completed: %s succeeded, %s failed, %s removed",
                    len(results["succeeded"]),
                    len(results["failed"]),
                    len(results["removed"]),
                )
        except Exception as e:  # Catch all exceptions to keep the Runner alive
            log.exception("Backup failed")
            lines = ["Backup failed unexpectedly with:", str(e)]
            BackupRunner._send_mail("Backup: unexpected errors", lines)

    @staticmethod
    def _check_cache_usage():
        """Log the current disk usage of the cache at an appropriate level."""
        total, used, free = shutil.disk_usage(Config.config.backup.cache_directory)
        percentage_used = 100 * used / total
        if percentage_used < Config.config.backup.warning_mark_percent:
            log.info("Current cache usage %.1f", percentage_used)
        else:
            log.warning("Current cache usage %.1f", percentage_used)
            lines = [f"Current cache usage: {percentage_used}"]
            BackupRunner._send_mail("Backup: high cache usage", lines)

    @staticmethod
    def _send_mail(subject: str, msg_lines: list[str]) -> None:
        """If configured, send an email notification for an error or warning."""
        if Config.config.backup.mail is not None:
            with SMTP(host=Config.config.backup.mail.host) as smtp:
                lines = [
                    f"From: {Config.config.backup.mail.from_addr}",
                    f"To: {','.join(Config.config.backup.mail.to_addrs)}",
                    f"Subject: {subject}",
                    "",  # Newline needed between headers and body
                ]
                lines += msg_lines
                smtp.sendmail(
                    from_addr=Config.config.backup.mail.from_addr,
                    to_addrs=Config.config.backup.mail.to_addrs,
                    msg="\r\n".join(lines),
                )
