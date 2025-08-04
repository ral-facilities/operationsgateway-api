from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.exceptions import MissingDocumentError
from operationsgateway_api.src.records.echo_interface import EchoInterface
from operationsgateway_api.src.records.float_image import FloatImage
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.vector import Vector
from operationsgateway_api.src.records.waveform import Waveform
from test.conftest import clear_lru_cache


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
        bucket = await echo.get_bucket()
        waveform_query = bucket.objects.filter(
            Prefix=f"{Waveform.echo_prefix}/{record_id}/",
        )
        async for waveform in waveform_query:
            pytest.fail(f"{waveform} still exists")

        image_query = bucket.objects.filter(
            Prefix=f"{Image.echo_prefix}/{record_id}/",
        )
        async for image in image_query:
            pytest.fail(f"{image} still exists")

        vector_query = bucket.objects.filter(
            Prefix=f"{Vector.echo_prefix}/{record_id}/",
        )
        async for vector in vector_query:
            pytest.fail(f"{vector} still exists")

        float_image_query = bucket.objects.filter(
            Prefix=f"{FloatImage.echo_prefix}/{record_id}/",
        )
        async for float_image in float_image_query:
            pytest.fail(f"{float_image} still exists")

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
        bucket = await echo.get_bucket()
        waveform_query = bucket.objects.filter(
            Prefix=f"{Waveform.echo_prefix}/{subdirectories}/",
        )
        async for waveform in waveform_query:
            pytest.fail(f"{waveform} still exists")

        image_query = bucket.objects.filter(
            Prefix=f"{Image.echo_prefix}/{subdirectories}/",
        )
        async for image in image_query:
            pytest.fail(f"{image} still exists")

        vector_query = bucket.objects.filter(
            Prefix=f"{Vector.echo_prefix}/{subdirectories}/",
        )
        async for vector in vector_query:
            pytest.fail(f"{vector} still exists")

        float_image_query = bucket.objects.filter(
            Prefix=f"{FloatImage.echo_prefix}/{subdirectories}/",
        )
        async for float_image in float_image_query:
            pytest.fail(f"{float_image} still exists")
