from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.exceptions import MissingDocumentError
from operationsgateway_api.src.records.echo_interface import EchoInterface
from operationsgateway_api.src.records.float_image import FloatImage
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.vector import Vector
from operationsgateway_api.src.records.waveform import Waveform


class TestDeleteRecordById:
    @pytest.mark.asyncio
    async def test_delete_record_success(
        self,
        test_app: TestClient,
        login_and_get_token,
        data_for_delete_records,
    ):
        record_id = 19000000000011
        delete_response = test_app.delete(
            f"/records/{record_id}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert delete_response.status_code == 204
        # Checks the record has been deleted from the database
        with pytest.raises(MissingDocumentError):
            await Record.find_record_by_id(record_id, {})

        # Check that waveform and image have been removed from Echo
        echo = EchoInterface()
        waveform_query = echo.bucket.objects.filter(
            Prefix=f"{Waveform.echo_prefix}/{record_id}/",
        )
        assert list(waveform_query) == []

        image_query = echo.bucket.objects.filter(
            Prefix=f"{Image.echo_prefix}/{record_id}/",
        )
        assert list(image_query) == []

        vector_query = echo.bucket.objects.filter(
            Prefix=f"{Vector.echo_prefix}/{record_id}/",
        )
        assert list(vector_query) == []

        float_image_query = echo.bucket.objects.filter(
            Prefix=f"{FloatImage.echo_prefix}/{record_id}/",
        )
        assert list(float_image_query) == []

    @pytest.mark.asyncio
    async def test_delete_record_subdirectories_success(
        self,
        test_app: TestClient,
        login_and_get_token,
        data_for_delete_records_subdirectories: str,
    ):
        delete_response = test_app.delete(
            f"/records/{data_for_delete_records_subdirectories}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert delete_response.status_code == 204
        # Checks the record has been deleted from the database
        with pytest.raises(MissingDocumentError):
            await Record.find_record_by_id(data_for_delete_records_subdirectories, {})

        # Check that waveform and image have been removed from Echo
        echo = EchoInterface()
        subdirectories = EchoInterface.format_record_id(
            data_for_delete_records_subdirectories,
        )
        waveform_query = echo.bucket.objects.filter(
            Prefix=f"{Waveform.echo_prefix}/{subdirectories}/",
        )
        assert list(waveform_query) == []

        image_query = echo.bucket.objects.filter(
            Prefix=f"{Image.echo_prefix}/{subdirectories}/",
        )
        assert list(image_query) == []

        vector_query = echo.bucket.objects.filter(
            Prefix=f"{Vector.echo_prefix}/{subdirectories}/",
        )
        assert list(vector_query) == []

        float_image_query = echo.bucket.objects.filter(
            Prefix=f"{FloatImage.echo_prefix}/{subdirectories}/",
        )
        assert list(float_image_query) == []
