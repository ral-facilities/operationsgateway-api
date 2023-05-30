from unittest.mock import mock_open, patch

import pytest

from operationsgateway_api.src.experiments.unique_worker import (
    assign_event_to_single_worker,
    UniqueWorker,
)


class TestUniqueWorker:
    # TODO - path doesn't seem to be mocking correctly
    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.worker_file_path",
        "test/path",
    )
    @patch("os.getpid", return_value=10)
    @patch(
        "operationsgateway_api.src.experiments.unique_worker.UniqueWorker"
        "._is_file_empty",
        return_value=True,
    )
    @patch(
        "operationsgateway_api.src.experiments.unique_worker.UniqueWorker._assign",
    )
    def test_init(self, mock_assign, _, __, remove_background_pid_file):
        test_worker = UniqueWorker()

        assert test_worker.id_ == "10"
        assert test_worker.file_empty
        assert test_worker.is_assigned
        assert mock_assign.call_count == 1

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.worker_file_path",
        "test/path",
    )
    @patch("os.getpid", return_value=10)
    @patch(
        "operationsgateway_api.src.experiments.unique_worker.UniqueWorker"
        "._is_file_empty",
        return_value=True,
    )
    @patch(
        "operationsgateway_api.src.experiments.unique_worker.UniqueWorker._assign",
    )
    @pytest.mark.parametrize(
        "file_pid, expected_return",
        [
            pytest.param("10", True, id="PID matches contents of file"),
            pytest.param("20", False, id="PID doesn't match contents of file"),
        ],
    )
    def test_does_pid_match_file(
        self,
        _,
        __,
        ___,
        file_pid,
        expected_return,
        remove_background_pid_file,
    ):
        test_worker = UniqueWorker()

        with patch(
            "operationsgateway_api.src.experiments.unique_worker.UniqueWorker"
            "._read_file",
            return_value=file_pid,
        ):
            pid_match = test_worker.does_pid_match_file()
            assert pid_match == expected_return

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.worker_file_path",
        "test/path",
    )
    @pytest.mark.parametrize(
        "expected_exception",
        [
            pytest.param(None, id="File removed as expected"),
            pytest.param(FileNotFoundError, id="File not found"),
        ],
    )
    def test_remove_file(self, expected_exception, remove_background_pid_file):
        with patch("os.remove", side_effect=expected_exception) as mock_remove:
            UniqueWorker.remove_file()
            assert mock_remove.call_count == 1

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.worker_file_path",
        "test/path",
    )
    @patch("os.getpid", return_value=10)
    @patch(
        "operationsgateway_api.src.experiments.unique_worker.UniqueWorker._assign",
    )
    @patch("os.mkdir")
    @pytest.mark.parametrize(
        "expected_return, mock_exception",
        [
            pytest.param(False, None, id="File is not empty"),
            pytest.param(True, None, id="File is empty"),
            pytest.param(
                True,
                FileNotFoundError,
                id="File not found, but is created (and therefore empty)",
            ),
        ],
    )
    def test_is_file_empty(
        self,
        _,
        __,
        ___,
        expected_return,
        mock_exception,
        remove_background_pid_file,
    ):
        file_pid = "" if expected_return else 10
        print(f"File PID: {file_pid}")

        with patch(
            "operationsgateway_api.src.experiments.unique_worker.UniqueWorker"
            "._is_file_empty",
            return_value=True,
        ):
            test_worker = UniqueWorker()

        with patch(
            "operationsgateway_api.src.experiments.unique_worker.UniqueWorker"
            "._read_file",
            return_value=file_pid,
            side_effect=mock_exception,
        ):
            file_empty = test_worker._is_file_empty()
            assert file_empty == expected_return

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.worker_file_path",
        "test/path",
    )
    @patch("os.getpid", return_value=10)
    @patch(
        "operationsgateway_api.src.experiments.unique_worker.UniqueWorker"
        "._is_file_empty",
        return_value=True,
    )
    @patch(
        "operationsgateway_api.src.experiments.unique_worker.UniqueWorker._assign",
    )
    def test_read_file(self, _, __, ___, remove_background_pid_file):
        test_worker = UniqueWorker()

        with patch("builtins.open", mock_open(read_data="123")):
            file_contents = test_worker._read_file()
            assert file_contents == "123"

    @pytest.mark.asyncio
    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.worker_file_path",
        "test/path",
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.app.reload",
        False,
    )
    @patch("os.getpid", return_value=10)
    @patch(
        "operationsgateway_api.src.experiments.unique_worker.UniqueWorker._assign",
    )
    @pytest.mark.parametrize(
        "pid_match, expected_output",
        [
            pytest.param(True, 1, id="No reload, PID match"),
            pytest.param(False, None, id="No reload, PID doesn't match"),
        ],
    )
    async def test_assign_decorator(
        self,
        _,
        __,
        pid_match,
        expected_output,
        remove_background_pid_file,
    ):
        @assign_event_to_single_worker()
        async def decorated_func():
            return 1

        with patch(
            "operationsgateway_api.src.experiments.unique_worker.UniqueWorker"
            ".does_pid_match_file",
            return_value=pid_match,
        ):
            output = await decorated_func()

        print(f"OP: {output}")
        assert output == expected_output

    @pytest.mark.asyncio
    @patch("operationsgateway_api.src.config.Config.config.app.reload", True)
    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.worker_file_path",
        "test/path",
    )
    @patch("os.getpid", return_value=10)
    @patch(
        "operationsgateway_api.src.experiments.unique_worker.UniqueWorker._assign",
    )
    @pytest.mark.parametrize(
        "file_empty, expected_output",
        [
            pytest.param(True, 1, id="Worker assigned"),
            pytest.param(False, None, id="Worker not assigned"),
        ],
    )
    async def test_assign_decorator_reload_enabled(
        self,
        _,
        __,
        file_empty,
        expected_output,
        remove_background_pid_file,
    ):
        with patch(
            "operationsgateway_api.src.experiments.unique_worker.UniqueWorker"
            "._is_file_empty",
            return_value=file_empty,
        ):

            @assign_event_to_single_worker()
            async def decorated_func():
                return 1

            output = await decorated_func()
            assert output == expected_output
