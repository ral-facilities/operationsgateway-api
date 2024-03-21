import pytest

from operationsgateway_api.src.exceptions import MissingDocumentError
from operationsgateway_api.src.models import WaveformModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.waveform import Waveform


class TestWaveform:
    test_waveform = WaveformModel(
        _id="19520605070023_test_waveform_id",
        x=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        y=[8.0, 3.0, 6.0, 2.0, 3.0, 8.0],
    )

    @pytest.mark.asyncio
    async def test_insert_waveform_success(self, remove_waveform_entry):
        # test will need to be changed with waveform echo changes

        waveform_instance = Waveform(TestWaveform.test_waveform)
        await waveform_instance.insert_waveform()

        waveform = await Waveform.get_waveform("19520605070023_test_waveform_id")

        assert waveform == TestWaveform.test_waveform

    @pytest.mark.asyncio
    async def test_insert_waveform_skipped(self, remove_waveform_entry):
        # test will need to be changed with waveform echo changes

        await MongoDBInterface.insert_one(
            "waveforms",
            TestWaveform.test_waveform.model_dump(by_alias=True),
        )

        waveform_instance = Waveform(TestWaveform.test_waveform)
        await waveform_instance.insert_waveform()

        waveform = await Waveform.get_waveform("19520605070023_test_waveform_id")

        assert waveform == TestWaveform.test_waveform

    @pytest.mark.asyncio
    async def test_waveform_not_found(self):
        with pytest.raises(MissingDocumentError, match="Waveform cannot be found"):
            await Waveform.get_waveform("19520605070023_test_waveform_id")
