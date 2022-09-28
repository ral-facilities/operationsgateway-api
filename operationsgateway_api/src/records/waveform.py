import base64
from io import BytesIO
import matplotlib.pyplot as plt

from operationsgateway_api.src.models import Waveform as WaveformModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface


class Waveform:
    def __init__(self, waveform: WaveformModel) -> None:
        self.waveform = waveform
        # TODO - do we need to declare this here if it's just None?
        self.thumbnail = None
        self.is_stored = False

    async def insert_waveform(self):
        await self._is_waveform_stored()
        if not self.is_stored:
            # TODO - might have to convert self.waveform into dict/JSON?
            await MongoDBInterface.insert_one("waveforms", self.waveform)

    def create_thumbnail(self):
        # Think base64 conversion function will be elsewhere?
        with BytesIO() as waveform_image_buffer:
            self._create_plot(waveform_image_buffer)
            self.thumbnail = base64.b64encode(waveform_image_buffer.getvalue())

    async def _is_waveform_stored(self) -> bool:
        waveform_exist = await MongoDBInterface.find_one(
            "waveforms", filter_={"_id": self.waveform.id_},
        )
        self.is_stored = True if waveform_exist else False

    # TODO - alternative to plt.?
    def _create_plot(self, buffer):
        # Making changes to plot so figure size and line width is correct and axes are
        # disabled
        plt.rcParams["figure.figsize"] = [1, 0.75]
        plt.xticks([])
        plt.yticks([])
        # TODO - if we go to storing x and y as strings in the model, this might break
        plt.plot(self.waveform.x, self.waveform.y, linewidth=0.5)
        plt.axis("off")
        plt.box(False)

        plt.savefig(buffer, format="PNG", bbox_inches="tight", pad_inches=0, dpi=130)
        # Flushes the plot to remove data from previously ingested waveforms
        plt.clf()

    @staticmethod
    async def get_waveform(waveform_id):
        return await MongoDBInterface.find_one(
            "waveforms",
            {"_id": waveform_id},
        )
