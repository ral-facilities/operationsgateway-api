import base64
from io import BytesIO
import json
import logging

import matplotlib.pyplot as plt

from operationsgateway_api.src.exceptions import MissingDocumentError
from operationsgateway_api.src.models import Waveform as WaveformModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface


log = logging.getLogger()


class Waveform:
    def __init__(self, waveform: WaveformModel) -> None:
        self.waveform = waveform
        self.thumbnail = None
        self.is_stored = False

    async def insert_waveform(self):
        await self._is_waveform_stored()
        if not self.is_stored:
            await MongoDBInterface.insert_one(
                "waveforms",
                self.waveform.dict(by_alias=True),
            )

    def create_thumbnail(self):
        # Think base64 conversion function will be elsewhere?
        with BytesIO() as waveform_image_buffer:
            self._create_plot(waveform_image_buffer)
            self.thumbnail = base64.b64encode(waveform_image_buffer.getvalue())

    def get_channel_name_from_id(self):
        """
        From a waveform ID, extract and return the channel name associated with the
        waveform. For example, 20220408140310_N_COMP_SPEC_TRACE -> N_COMP_SPEC_TRACE
        """
        return "_".join(self.waveform.id_.split("_")[1:])

    async def _is_waveform_stored(self) -> bool:
        waveform_exist = await MongoDBInterface.find_one(
            "waveforms",
            filter_={"_id": self.waveform.id_},
        )
        self.is_stored = True if waveform_exist else False

    # TODO 1 - alternative to plt.?
    def _create_plot(self, buffer):
        # Making changes to plot so figure size and line width is correct and axes are
        # disabled
        plt.rcParams["figure.figsize"] = [1, 0.75]
        plt.xticks([])
        plt.yticks([])
        plt.plot(
            json.loads(self.waveform.x),
            json.loads(self.waveform.y),
            linewidth=0.5,
        )
        plt.axis("off")
        plt.box(False)

        plt.savefig(buffer, format="PNG", bbox_inches="tight", pad_inches=0, dpi=130)
        # Flushes the plot to remove data from previously ingested waveforms
        plt.clf()

    @staticmethod
    async def get_waveform(waveform_id):
        waveform_data = await MongoDBInterface.find_one(
            "waveforms",
            {"_id": waveform_id},
        )

        if waveform_data:
            return WaveformModel(**waveform_data)
        else:
            log.error("Waveform cannot be found, ID: %s", waveform_id)
            raise MissingDocumentError("Waveform cannot be found")
