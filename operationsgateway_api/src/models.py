from datetime import datetime
from typing import ClassVar, Dict, List, Literal, Optional, Union

import numpy as np
from pydantic import BaseModel, Field, root_validator, validator

from operationsgateway_api.src.exceptions import ChannelManifestError


class ImageModel(BaseModel):
    path: str
    data: np.ndarray

    class Config:
        arbitrary_types_allowed = True


class WaveformModel(BaseModel):
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


class ImageChannelMetadataModel(BaseModel):
    channel_dtype: str
    exposure_time_s: Optional[float]
    gain: Optional[float]
    x_pixel_size: Optional[float]
    # TODO - UTF8 issue? \u00b5m
    x_pixel_units: Optional[str]
    y_pixel_size: Optional[float]
    y_pixel_units: Optional[str]


class ImageChannelModel(BaseModel):
    metadata: ImageChannelMetadataModel
    image_path: str
    thumbnail: Optional[str]


class ScalarChannelMetadataModel(BaseModel):
    channel_dtype: str
    units: Optional[str]


class ScalarChannelModel(BaseModel):
    metadata: ScalarChannelMetadataModel
    data: Union[int, float, str]

    class Config:
        smart_union = True


class WaveformChannelMetadataModel(BaseModel):
    channel_dtype: str
    x_units: Optional[str]
    y_units: Optional[str]


class WaveformChannelModel(BaseModel):
    metadata: WaveformChannelMetadataModel
    thumbnail: Optional[str]
    waveform_id: str


class RecordMetadataModel(BaseModel):
    epac_ops_data_version: str
    shotnum: Optional[int]
    timestamp: datetime


class RecordModel(BaseModel):
    id_: str = Field(alias="_id")
    metadata: RecordMetadataModel
    channels: Dict[
        str,
        Union[ImageChannelModel, ScalarChannelModel, WaveformChannelModel],
    ]


class LoginDetailsModel(BaseModel):
    username: str
    password: str


class AccessTokenModel(BaseModel):
    token: str


class UserModel(BaseModel):
    username: str = Field(alias="_id")
    sha256_password: Optional[str]
    auth_type: str
    authorised_routes: Optional[List[str]]


class ChannelModel(BaseModel):
    # Field names where modifications to the data cannot be made
    protected_fields: ClassVar[List[str]] = ["type_", "units"]

    name: str
    path: str
    type_: Optional[Literal["scalar", "image", "waveform"]] = Field(alias="type")

    # Should the value be displayed as it is stored or be shown in x10^n format
    notation: Optional[Literal["scientific", "normal"]]
    # Number of significant figures used to display the value
    precision: Optional[int]
    units: Optional[str]
    historical: Optional[bool]

    x_units: Optional[str]
    y_units: Optional[str]

    @root_validator(pre=True)
    def set_default_type(cls, values):  # noqa: B902, N805
        values.setdefault("type", "scalar")
        return values

    @validator("x_units", "y_units")
    def check_waveform_channel(cls, v, values):  # noqa: B902, N805
        if not values["type_"] == "waveform":
            raise ChannelManifestError(
                "Only waveform channels should contain waveform channel metadata."
                f" Invalid channel is called: {values['name']}",
            )
        else:
            return v


class ChannelManifestModel(BaseModel):
    id_: str = Field(alias="_id")
    channels: Dict[str, ChannelModel]


class ChannelSummaryModel(BaseModel):
    first_date: datetime
    most_recent_date: datetime
    recent_sample: List[Union[int, float, str]]

    class Config:
        smart_union = True
