from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from bson import ObjectId
import numpy as np
from pydantic import BaseModel, Field, validator


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")

        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


# TODO - has this been used?
class RecordsQueryParams:
    filter_: dict
    skip: int
    limit: int
    order: Optional[List[str]]
    projection: Optional[List[str]]


# TODO - Not sure if I'll need this or not
class Channel(BaseModel):
    pass


class Image(BaseModel):
    path: str
    # TODO - data, name and type
    data: Any


class Waveform(BaseModel):
    id_: str = Field(alias="_id")
    # TODO - probably should change this to str only to match how it's stored in DB
    x: str
    y: str

    @validator("x", "y", pre=True, always=True)
    def encode_values(cls, value):
        if isinstance(value, np.ndarray):
            return str(list(value))
        else:
            # Typically will be a string when putting waveform data into the model from
            # results of a MongoDB query
            return value


class ImageChannelMetadata(BaseModel):
    # TODO - could we have a channel data type model to restrict acceptable values:
    # export type DataType = 'scalar' | 'image' | 'waveform';
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
    # TODO - check the type on this works, shot num channel should still be an integer
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


# TODO - rename when I've removed the original Record model above
class Record(BaseModel):
    id_: str = Field(alias="_id")
    metadata: RecordMetadata
    # TODO - channels type
    channels: Dict[str, Union[ImageChannel, ScalarChannel, WaveformChannel]]
