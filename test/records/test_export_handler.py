import pytest

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
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
    @pytest.mark.parametrize(
        ["channel_name"],
        [
            pytest.param("FE-204-NSS-CAM-1", id="Image"),
            pytest.param("FE-204-NSS-SP", id="Waveform"),
            pytest.param("FE-204-NSS-WFS", id="Float image"),
            pytest.param("FE-204-NSS-WFS-COEF", id="Vector"),
        ],
    )
    async def test_process_channel(self, channel_name: str):
        export_handler = ExportHandler(
            records_data=[],
            channel_manifest=await ChannelManifest.get_most_recent_manifest(),
            projection=[],
            lower_level=0,
            upper_level=255,
            limit_bit_depth=8,
            colourmap_name="viridis",
            functions=[],
            export_scalars=True,
            export_images=True,
            export_float_images=True,
            export_waveform_images=True,
            export_waveform_csvs=True,
            export_vector_images=True,
            export_vector_csvs=True,
        )
        await export_handler._process_data_channel(
            channels={},
            record_id="20230605080300",
            channel_name=channel_name,
            line="",
        )
