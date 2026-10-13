from __future__ import annotations

from io import BytesIO
import logging

import numpy as np
from PIL import Image as PILImage, PngImagePlugin

from operationsgateway_api.src.exceptions import (
    EchoS3Error,
    MissingAttributeError,
    QueryParameterError,
    RecordError,
)
from operationsgateway_api.src.models import (
    ChannelDtype,
    PartialImageSeriesChannelModel,
)
from operationsgateway_api.src.records.echo_interface import get_echo_interface
from operationsgateway_api.src.records.greyscale_image_abc import GreyscaleImageABC
from operationsgateway_api.src.records.image_abc import ImageABC
from operationsgateway_api.src.records.record import Record

log = logging.getLogger()


class ImageSeries(GreyscaleImageABC):
    echo_prefix = "image_series"
    echo_extension = "npy"

    def create_thumbnail(self) -> None:
        # The thumbnail represents the first frame. The data has already been
        # normalised to 8 or 16 bit, so it can be used as it is.
        self._create_greyscale_thumbnail(self.image.data[0])

    @staticmethod
    def get_storage_dtype(bit_depth: int) -> np.dtype:
        """Given the bit depth, return the numpy dtype that sets bytes per pixel."""
        if bit_depth <= 8:
            dtype = np.uint8
        else:
            dtype = np.uint16
        return np.dtype(dtype)

    @staticmethod
    def write_npy_header(
        file_object: BytesIO,
        shape: tuple[int, ...],
        dtype: np.dtype,
    ) -> None:
        # before the numpy data (of images) we write a header so we
        # know what the data contains
        np.lib.format.write_array_header_1_0(
            file_object,
            {
                # "descr" is the key the .npy format requires for the dtype of the array
                "descr": np.lib.format.dtype_to_descr(dtype),
                # makes sure the data is stored in series order
                "fortran_order": False,
                # for example: [number of images, height, width]
                "shape": shape,
            },
        )

    @staticmethod
    def get_header_offset_bytes(shape: tuple[int, ...], dtype: np.dtype) -> int:
        """
        Work out the offset of the numpy header in bytes, so we know where the data
        starts
        """
        header = BytesIO()
        ImageSeries.write_npy_header(header, shape, dtype)
        return header.tell()

    @staticmethod
    async def upload_image(input_image: ImageABC) -> str | None:
        """
        Upload the image series to Echo
        """
        log.info("Storing image in a Bytes object: %s", input_image.image.path)

        # The data is already uint8 or uint16, having been normalised in `__init__`
        data = np.ascontiguousarray(input_image.image.data)

        image_bytes = BytesIO()
        ImageSeries.write_npy_header(image_bytes, data.shape, data.dtype)

        # Append the contiguous pixel bytes after the header.
        image_bytes.write(data.data.cast("B"))

        echo_interface = get_echo_interface()
        storage_path = input_image.get_full_path(input_image.image.path)
        log.info("Storing image on S3: %s", storage_path)

        try:
            await echo_interface.upload_file_object(image_bytes, storage_path)
            return None
        except EchoS3Error:
            # Extract the channel name and propagate it
            channel_name = input_image.get_channel_name_from_path()
            log.error("Failed to upload image series for channel: %s", channel_name)
            return channel_name

    @staticmethod
    async def get_frame(
        record_id: str,
        channel_name: str,
        frame_index: int,
    ) -> bytes:
        """
        This doesn't just get any old frame! but it works out where each frame
        is by calculate the requested frame's byte range. It uses the header offset,
        frame index, dimensions, and bytes per pixel, then retrieve it as a
        greyscale PNG.
        """

        log.info(
            "Retrieving frame %d for channel %s in record %s",
            frame_index,
            channel_name,
            record_id,
        )

        record = await Record.find_record_by_id(record_id, {})
        channel = (record.channels or {}).get(channel_name)

        if channel is None:
            raise MissingAttributeError(
                f"Channel '{channel_name}' not found in record '{record_id}'",
            )

        if not isinstance(channel, PartialImageSeriesChannelModel):
            raise QueryParameterError("Channel is not an image series")

        metadata = channel.metadata
        if metadata is None or metadata.channel_dtype != ChannelDtype.IMAGE_SERIES:
            raise RecordError("Image series metadata is missing or invalid")

        shape = channel.shape
        header_offset = channel.header_offset_bytes
        image_path = channel.image_path
        bit_depth = metadata.bit_depth

        if (
            shape is None
            or any(dimension <= 0 for dimension in shape)
            or header_offset is None
            or header_offset <= 0
            or not image_path
            or not isinstance(bit_depth, int)
        ):
            raise RecordError("Image series storage metadata is missing or invalid")

        frame_count, height, width = shape

        if not 0 <= frame_index < frame_count:
            raise QueryParameterError(
                f"Frame index must be between 0 and {frame_count - 1}",
            )

        # Every frame in a series has the same bit depth, and so the same width
        storage_dtype = ImageSeries.get_storage_dtype(bit_depth)

        # Each frame occupies consecutive bytes after the NPY header.
        frame_size = height * width * storage_dtype.itemsize
        start_byte = header_offset + frame_index * frame_size
        end_byte = start_byte + frame_size - 1

        pixel_bytes = await get_echo_interface().download_file_range(
            object_path=ImageSeries.get_full_path(image_path),
            start_byte=start_byte,
            end_byte=end_byte,
        )

        frame = np.frombuffer(pixel_bytes, dtype=storage_dtype).reshape(height, width)

        output = BytesIO()
        with PILImage.fromarray(frame) as image:
            # As for normal images, record the original bit depth in the PNG
            if 0 < bit_depth <= 16:
                info = PngImagePlugin.PngInfo()
                info.add(b"sBIT", bit_depth.to_bytes(1, byteorder="big"))
                image.save(output, format="PNG", pnginfo=info)
            else:
                image.save(output, format="PNG")

        return output.getvalue()

    @staticmethod
    async def get_image(
        record_id: str,
        channel_name: str,
        frame_index: int,
        original_image: bool,
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
        colourmap_name: str,
    ) -> bytes:
        """
        Retrieve one frame of an image series and return the bytes of the image
        depending on what the user has requested.

        This is the equivalent of `Image.get_image` for a single frame. If
        'original_image' is set to True then the unprocessed frame is returned,
        otherwise false colour is applied using the parameters provided.
        """
        png_bytes = await ImageSeries.get_frame(
            record_id=record_id,
            channel_name=channel_name,
            frame_index=frame_index,
        )
        return ImageSeries.apply_false_colour(
            image_bytes=png_bytes,
            original_image=original_image,
            lower_level=lower_level,
            upper_level=upper_level,
            limit_bit_depth=limit_bit_depth,
            colourmap_name=colourmap_name,
        )
