from unittest.mock import MagicMock, patch

import pytest

from operationsgateway_api.src.backup.backup_runner import BackupRunner, log


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

        log.info.assert_called_with("Current cache usage %.1f%%", 10.0)

    def test_check_cache_usage_high(self) -> None:
        log.warning = MagicMock(wraps=log.warning)
        target = "operationsgateway_api.src.backup.backup_runner.shutil.disk_usage"
        disk_usage = MagicMock()
        disk_usage.return_value = (10, 9, 1)
        with patch(target, disk_usage):
            BackupRunner._check_cache_usage()

        log.warning.assert_called_with("Current cache usage %.1f%%", 90.0)
