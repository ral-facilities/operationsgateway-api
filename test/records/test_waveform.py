import pytest

from operationsgateway_api.src.exceptions import WaveformError
from operationsgateway_api.src.models import WaveformModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.waveform import Waveform


class TestWaveform:
    test_waveform = WaveformModel(
        path="19520605070023/test-channel-name.json",
        x=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        y=[8.0, 3.0, 6.0, 2.0, 3.0, 8.0],
    )

    @pytest.mark.asyncio
    async def test_insert_waveform_success(self, remove_waveform_entry):
        waveform_instance = Waveform(TestWaveform.test_waveform)
        waveform_instance.insert_waveform()

        waveform = Waveform.get_waveform("19520605070023/test-channel-name.json")

        assert waveform.model_dump() == TestWaveform.test_waveform.model_dump()

    @pytest.mark.asyncio
    async def test_waveform_not_found(self):
        with pytest.raises(WaveformError, match="Waveform could not be found"):
            Waveform.get_waveform("19520605070023/test-channel-name.json")
