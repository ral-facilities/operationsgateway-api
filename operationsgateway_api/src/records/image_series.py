from __future__ import annotations

from io import BytesIO

import numpy as np

from operationsgateway_api.src.exceptions import EchoS3Error
from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.records.echo_interface import get_echo_interface
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.image_abc import ImageABC


# pretty much a copy paste from the image class
class ImageSeries(ImageABC):
    echo_prefix = "image_series"
    echo_extension = "npy"
    storage_dtype = np.dtype("<u2")

    def __init__(self, image: ImageModel) -> None:
        super().__init__(image)

    def write_npy_header(self, file_object: BytesIO, shape: tuple[int, ...]) -> None:
        # before the numpy data (of images) we write a header so we know what the data contains
        np.lib.format.write_array_header_1_0(
            file_object,
            {
                "descr": np.lib.format.dtype_to_descr(self.storage_dtype),
                "fortran_order": False,  # this option makes sure the data is stored in series order
                "shape": shape,  # [number of images, height, width]
            },
        )

    def get_header_offset_bytes(self, data: np.ndarray) -> int:
        header = BytesIO()
        self.write_npy_header(header, data.shape)
        return header.tell()

    def create_thumbnail(self) -> None:
        # Use a separate copy of frame zero for PNG processing.
        preview = Image(
            ImageModel(
                path=self.image.path,
                data=self.image.data[0].copy(),
                bit_depth=self.image.bit_depth,
            ),
        )
        preview.create_thumbnail()
        self.thumbnail = preview.thumbnail

    @staticmethod
    async def upload_image(input_image: ImageSeries) -> str | None:
        # Convert for storage without rescaling pixel values.
        data = np.ascontiguousarray(
            input_image.image.data,
            dtype=input_image.storage_dtype,
        )

        image_bytes = BytesIO()
        input_image.write_npy_header(image_bytes, data.shape)

        # Append the contiguous pixel bytes after the header.
        image_bytes.write(data.data.cast("B"))

        storage_path = input_image.get_full_path(input_image.image.path)

        try:
            await get_echo_interface().upload_file_object(image_bytes, storage_path)
            return None
        except EchoS3Error:
            return input_image.get_channel_name_from_path()

    @staticmethod
    async def get_image(
        record_id: str, channel_name: str, colourmap_name: str
    ) -> BytesIO:
        raise NotImplementedError(
            "TDDO: Frame retrieval will be implemented later",
        )

    @staticmethod
    async def get_preferred_colourmap(access_token: str) -> str:
        return await Image.get_preferred_colourmap(access_token)
