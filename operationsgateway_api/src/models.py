from datetime import datetime
from typing import Any, ClassVar, Dict, List, Literal, Optional, Union

from bson.objectid import ObjectId
import numpy as np
from pydantic import BaseModel, Field, root_validator, validator

from operationsgateway_api.src.exceptions import ChannelManifestError, ModelError


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, ObjectId):
            raise TypeError("ObjectId required")
        return str(v)


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
    def encode_values(cls, value):
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
    def set_default_type(cls, values):
        values.setdefault("type", "scalar")
        return values

    @validator("x_units", "y_units")
    def check_waveform_channel(cls, v, values):
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
    recent_sample: List[Dict[datetime, Union[int, float, str]]]

    class Config:
        smart_union = True


class ExperimentModel(BaseModel):
    id_: Optional[PyObjectId] = Field(alias="_id")
    experiment_id: str
    part: int
    start_date: datetime
    end_date: datetime

    class Config:
        arbitrary_types_allowed = True


class ShotnumConverterRange(BaseModel):
    opposite_range_fields: ClassVar[Dict[str, str]] = {"from": "min_", "to": "max_"}

    min_: Union[int, datetime] = Field(alias="min")
    max_: Union[int, datetime] = Field(alias="max")

    @validator("max_")
    def validate_min_max(cls, value, values):  # noqa: B902, N805
        if value < values["min_"]:
            raise ModelError("max cannot be less than min value")
        else:
            return value


class DateConverterRange(BaseModel):
    opposite_range_fields: ClassVar[Dict[str, str]] = {"min": "from_", "max": "to"}

    from_: Union[int, datetime] = Field(alias="from")
    to: Union[int, datetime]

    @validator("to")
    def validate_min_max(cls, value, values):  # noqa: B902, N805
        if value < values["from_"]:
            raise ModelError("to cannot be less than from value")
        else:
            return value


class UserSessionModel(BaseModel):
    id_: Optional[PyObjectId] = Field(alias="_id")
    username: str
    name: str
    summary: str
    timestamp: datetime
    auto_saved: bool
    session: Dict[str, Any]

    class Config:
        arbitrary_types_allowed = True


class UserSessionListModel(UserSessionModel):
    # Make fields optional that aren't needed in the session list and exclude them from
    # displaying on output
    username: Optional[str]
    session: Optional[Dict[str, Any]]

    class Config:
        fields = {"username": {"exclude": True}, "session": {"exclude": True}}
