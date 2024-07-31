import base64
from io import BytesIO
from unittest.mock import patch

from PIL import Image
import pytest

from operationsgateway_api.src.exceptions import WaveformError
from operationsgateway_api.src.models import WaveformModel
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

    @pytest.mark.parametrize(
        "config_thumbnail_size",
        [
            pytest.param((50, 50), id="50x50 thumbnail (square)"),
            pytest.param((60, 80), id="60x80 thumbnail (portrait)"),
            pytest.param((90, 40), id="90x40 thumbnail (landscape)"),
            pytest.param((75, 100), id="75x100 thumbnail (portrait)"),
        ],
    )
    def test_create_thumbnail_plot_size(self, config_thumbnail_size):
        test_waveform = Waveform(TestWaveform.test_waveform)
        with patch(
            "operationsgateway_api.src.config.Config.config.waveforms.thumbnail_size",
            config_thumbnail_size,
        ):
            test_waveform.create_thumbnail()

        bytes_thumbnail = base64.b64decode(test_waveform.thumbnail)
        img = Image.open(BytesIO(bytes_thumbnail))
        assert img.size == config_thumbnail_size
