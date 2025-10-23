from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from operationsgateway_api.src.backup.backup_runner import BackupRunner, log
from operationsgateway_api.src.config import BackupConfig


@pytest.fixture
def mocked_config(tmp_path: Path) -> Generator[BackupConfig, None, None]:
    backup = BackupConfig(
        cache_directory=tmp_path,
        target_url="",
        copy_cron_string="* * * * *",
        worker_file_path="",
    )
    with patch("operationsgateway_api.src.config.Config.config.backup", backup):
        yield backup


class TestBackupRunner:
    @pytest.mark.asyncio
    async def test_run_task_success(self, mocked_config: BackupConfig) -> None:
        return_value = {"succeeded": ["/path"], "failed": [], "removed": []}
        backup_runner = BackupRunner()
        backup_runner.x_root_d_client.backup = MagicMock()
        backup_runner.x_root_d_client.backup.return_value = return_value
        log.info = MagicMock(wraps=log.info)

        await backup_runner.run_task()

        msg = "Backup completed: %s succeeded, %s failed, %s removed"
        log.info.assert_called_with(msg, 1, 0, 0)

    @pytest.mark.asyncio
    async def test_run_task_failure(self, mocked_config: BackupConfig) -> None:
        return_value = {"succeeded": [], "failed": ["/path"], "removed": []}
        backup_runner = BackupRunner()
        backup_runner.x_root_d_client.backup = MagicMock()
        backup_runner.x_root_d_client.backup.return_value = return_value
        log.warning = MagicMock(wraps=log.warning)

        await backup_runner.run_task()

        msg = "Backup completed: %s succeeded, %s failed, %s removed"
        log.warning.assert_called_with(msg, 0, 1, 0)

    @pytest.mark.asyncio
    async def test_run_task_error(self, mocked_config: BackupConfig) -> None:
        backup_runner = BackupRunner()
        backup_runner.x_root_d_client.backup = MagicMock()
        backup_runner.x_root_d_client.backup.side_effect = RuntimeError("test")
        log.exception = MagicMock(wraps=log.exception)

        await backup_runner.run_task()

        log.exception.assert_called_with("Backup failed")

    def test_check_cache_usage_low(self, mocked_config: BackupConfig) -> None:
        log.info = MagicMock(wraps=log.info)
        target = "operationsgateway_api.src.backup.backup_runner.shutil.disk_usage"
        disk_usage = MagicMock()
        disk_usage.return_value = (10, 1, 9)
        with patch(target, disk_usage):
            BackupRunner._check_cache_usage()

        log.info.assert_called_with("Current cache usage %.1f%%", 10.0)

    def test_check_cache_usage_high(self, mocked_config: BackupConfig) -> None:
        log.warning = MagicMock(wraps=log.warning)
        target = "operationsgateway_api.src.backup.backup_runner.shutil.disk_usage"
        disk_usage = MagicMock()
        disk_usage.return_value = (10, 9, 1)
        with patch(target, disk_usage):
            BackupRunner._check_cache_usage()

        log.warning.assert_called_with("Current cache usage %.1f%%", 90.0)

    def test_validate_environment_variables_file_not_found(
        self,
        mocked_config: BackupConfig,
    ) -> None:
        match = (
            "Keytab file path neither defined in config.yml nor environment variable."
        )
        with pytest.raises(FileNotFoundError, match=match):
            BackupRunner.validate_environment_variables()

    def test_validate_environment_variables_permission(self, tmp_path: Path) -> None:
        match = "Keytab file permissions must be '600', but they were '644'"
        keytab_file_path = tmp_path / ".keytab"
        keytab_file_path.write_text("")
        backup = BackupConfig(
            cache_directory=tmp_path,
            target_url="",
            copy_cron_string="* * * * *",
            worker_file_path="",
            keytab_file_path=keytab_file_path,
        )
        with (
            patch("operationsgateway_api.src.config.Config.config.backup", backup),
            pytest.raises(PermissionError, match=match),
        ):
            BackupRunner.validate_environment_variables()
