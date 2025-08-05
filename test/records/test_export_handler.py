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

    @pytest.mark.asyncio
    async def test_process_projection(self):
        proj = "unrecognised.projection"
        export_handler = ExportHandler(
            [],
            None,
            [],
            0,
            255,
            8,
            None,
            [],
            False,
            False,
            False,
            False,
            False,
            False,
            False,
        )
        assert await export_handler._process_projection(None, {}, proj) == ""
