from unittest.mock import MagicMock, patch

import pytest

from operationsgateway_api.src.backup.backup_runner import BackupRunner, log
from operationsgateway_api.src.config import MailConfig


class TestBackupRunner:
    @pytest.mark.asyncio
    async def test_run_task_success(self) -> None:
        return_value = {"succeeded": ["/path"], "failed": [], "removed": []}
        backup_runner = BackupRunner()
        backup_runner.x_root_d_client.backup = MagicMock()
        backup_runner.x_root_d_client.backup.return_value = return_value
        log.info = MagicMock(wraps=log.info)

        await backup_runner.run_task()

        msg = "Backup completed: %s succeeded, %s failed, %s removed"
        log.info.assert_called_with(msg, 1, 0, 0)

    @pytest.mark.asyncio
    async def test_run_task_failure(self) -> None:
        return_value = {"succeeded": [], "failed": ["/path"], "removed": []}
        backup_runner = BackupRunner()
        backup_runner.x_root_d_client.backup = MagicMock()
        backup_runner.x_root_d_client.backup.return_value = return_value
        log.warning = MagicMock(wraps=log.warning)

        await backup_runner.run_task()

        msg = "Backup completed: %s succeeded, %s failed, %s removed"
        log.warning.assert_called_with(msg, 0, 1, 0)

    @pytest.mark.asyncio
    async def test_run_task_error(self) -> None:
        backup_runner = BackupRunner()
        backup_runner.x_root_d_client.backup = MagicMock()
        backup_runner.x_root_d_client.backup.side_effect = RuntimeError("test")
        log.exception = MagicMock(wraps=log.exception)

        await backup_runner.run_task()

        log.exception.assert_called_with("Backup failed")

    def test_check_cache_usage_low(self) -> None:
        log.info = MagicMock(wraps=log.info)
        target = "operationsgateway_api.src.backup.backup_runner.shutil.disk_usage"
        disk_usage = MagicMock()
        disk_usage.return_value = (10, 1, 9)
        with patch(target, disk_usage):
            BackupRunner._check_cache_usage()

        log.info.assert_called_with("Current cache usage %.1f", 10.0)

    def test_check_cache_usage_high(self) -> None:
        log.warning = MagicMock(wraps=log.warning)
        target = "operationsgateway_api.src.backup.backup_runner.shutil.disk_usage"
        disk_usage = MagicMock()
        disk_usage.return_value = (10, 9, 1)
        with patch(target, disk_usage):
            BackupRunner._check_cache_usage()

        log.warning.assert_called_with("Current cache usage %.1f", 90.0)

    def test_send_mail(self) -> None:
        config_target = "operationsgateway_api.src.config.Config.config.backup.mail"
        smtp_target = "operationsgateway_api.src.backup.backup_runner.SMTP"
        mail_config = MailConfig(
            host="localhost",
            to_addrs=["person1@stfc.ac.uk", "person2@stfc.ac.uk"],
            from_addr="no-reply@operationsgateway.stfc.ac.uk",
        )
        smtp_mock = MagicMock()
        with patch(config_target, mail_config), patch(smtp_target, smtp_mock):
            BackupRunner._send_mail("Test subject", ["Line 1", "", "Line 3"])

        msg = (
            "From: no-reply@operationsgateway.stfc.ac.uk\r\n"
            "To: person1@stfc.ac.uk,person2@stfc.ac.uk\r\n"
            "Subject: Test subject\r\n"
            "\r\n"
            "Line 1\r\n"
            "\r\n"
            "Line 3"
        )
        smtp_mock.assert_called_once_with(host="localhost")
        smtp_mock.return_value.__enter__.return_value.sendmail.assert_called_once_with(
            from_addr=mail_config.from_addr,
            to_addrs=mail_config.to_addrs,
            msg=msg,
        )
