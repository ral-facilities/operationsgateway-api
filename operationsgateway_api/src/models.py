from datetime import datetime
from typing import Dict, Optional, Union

import numpy as np
from pydantic import BaseModel, Field, validator


class Image(BaseModel):
    path: str
    data: np.ndarray

    class Config:
        arbitrary_types_allowed = True


class Waveform(BaseModel):
    id_: str = Field(alias="_id")
    x: str
    y: str

    @validator("x", "y", pre=True, always=True)
    def encode_values(cls, value):  # noqa: B902, N805
        if isinstance(value, np.ndarray):
            return str(list(value))
        else:
            # Typically will be a string when putting waveform data into the model from
            # results of a MongoDB query
            return value


class ImageChannelMetadata(BaseModel):
    channel_dtype: str
    exposure_time_s: Optional[float]
    gain: Optional[float]
    x_pixel_size: Optional[float]
    # TODO - UTF8 issue? \u00b5m
    x_pixel_units: Optional[str]
    y_pixel_size: Optional[float]
    y_pixel_units: Optional[str]


class ImageChannel(BaseModel):
    metadata: ImageChannelMetadata
    image_path: str
    thumbnail: Optional[str]


class ScalarChannelMetadata(BaseModel):
    channel_dtype: str
    units: Optional[str]


class ScalarChannel(BaseModel):
    metadata: ScalarChannelMetadata
    data: Union[float, int, str]


class WaveformChannelMetadata(BaseModel):
    channel_dtype: str
    x_units: Optional[str]
    y_units: Optional[str]


class WaveformChannel(BaseModel):
    metadata: WaveformChannelMetadata
    thumbnail: Optional[str]
    waveform_id: str


class RecordMetadata(BaseModel):
    epac_ops_data_version: str
    # TODO - if there's no shotnum, it ingested as null. Don't want this
    shotnum: Optional[int]
    timestamp: datetime


class Record(BaseModel):
    id_: str = Field(alias="_id")
    metadata: RecordMetadata
    channels: Dict[str, Union[ImageChannel, ScalarChannel, WaveformChannel]]
