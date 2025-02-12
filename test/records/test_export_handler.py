import pytest

from operationsgateway_api.src.models import (
    PartialWaveformChannelModel,
    WaveformChannelMetadataModel,
)
from operationsgateway_api.src.records.export_handler import ExportHandler


class TestExportHandler:
    @pytest.mark.parametrize(
        ["channel"],
        [
            pytest.param(PartialWaveformChannelModel()),
            pytest.param(
                PartialWaveformChannelModel(metadata=WaveformChannelMetadataModel()),
            ),
            pytest.param(
                PartialWaveformChannelModel(
                    metadata=WaveformChannelMetadataModel(
                        x_units="x_units",
                        y_units="y_units",
                    ),
                ),
            ),
        ],
    )
    def test_ensure_waveform_metadata(self, channel: PartialWaveformChannelModel):
        ExportHandler._ensure_waveform_metadata(channel=channel)
        assert channel.metadata is not None
        assert channel.metadata.x_units is not None
        assert channel.metadata.y_units is not None
