from datetime import datetime
from typing import Any, Callable, ClassVar, Dict, List, Literal, Optional, Union

from bson.objectid import ObjectId
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import core_schema
from typing_extensions import Annotated

from operationsgateway_api.src.exceptions import ChannelManifestError, ModelError


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        def validate_from_str(input_value: str) -> ObjectId:
            return ObjectId(input_value)

        return core_schema.union_schema(
            [
                # check if it's an instance first before doing any further work
                core_schema.is_instance_schema(ObjectId),
                core_schema.no_info_plain_validator_function(validate_from_str),
            ],
            serialization=core_schema.to_string_ser_schema(),
        )


class ImageModel(BaseModel):
    path: str
    data: np.ndarray
    model_config = ConfigDict(arbitrary_types_allowed=True)


class WaveformModel(BaseModel):
    id_: str = Field(alias="_id")
    x: List[float]
    y: List[float]

    class Config:
        arbitrary_types_allowed = True

    @field_validator("x", "y", mode="before")
    def encode_values(cls, value):  # noqa: N805
        if isinstance(value, np.ndarray):
            return list(value)
        else:
            return value


class ImageChannelMetadataModel(BaseModel):
    channel_dtype: str
    exposure_time_s: Optional[float] = None
    gain: Optional[float] = None
    x_pixel_size: Optional[float] = None
    x_pixel_units: Optional[str] = None
    y_pixel_size: Optional[float] = None
    y_pixel_units: Optional[str] = None


class ImageChannelModel(BaseModel):
    metadata: ImageChannelMetadataModel
    image_path: str
    thumbnail: Optional[str] = None


class ScalarChannelMetadataModel(BaseModel):
    channel_dtype: str
    units: Optional[str] = None


class ScalarChannelModel(BaseModel):
    metadata: ScalarChannelMetadataModel
    data: Union[int, float, str]


class WaveformChannelMetadataModel(BaseModel):
    channel_dtype: str
    x_units: Optional[str] = None
    y_units: Optional[str] = None


class WaveformChannelModel(BaseModel):
    metadata: WaveformChannelMetadataModel
    thumbnail: Optional[str] = None
    waveform_id: str


class RecordMetadataModel(BaseModel):
    epac_ops_data_version: str
    shotnum: Optional[int] = None
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
    sha256_password: Optional[str] = None
    auth_type: str
    authorised_routes: Optional[List[str]] = None


class ChannelModel(BaseModel):
    # Field names where modifications to the data cannot be made
    protected_fields: ClassVar[List[str]] = ["type_", "units"]

    name: str
    path: str
    type_: Optional[Literal["scalar", "image", "waveform"]] = Field(None, alias="type")

    # Should the value be displayed as it is stored or be shown in x10^n format
    notation: Optional[Literal["scientific", "normal"]] = None
    # Number of significant figures used to display the value
    precision: Optional[int] = None
    units: Optional[str] = None
    historical: Optional[bool] = None

    x_units: Optional[str] = None
    y_units: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def set_default_type(cls, values):
        values.setdefault("type", "scalar")
        return values

    @field_validator("x_units", "y_units")
    def check_waveform_channel(cls, v, values):  # noqa: N805
        if not values.data["type_"] == "waveform":
            raise ChannelManifestError(
                "Only waveform channels should contain waveform channel metadata."
                f" Invalid channel is called: {values.data['name']}",
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


class ExperimentModel(BaseModel):
    id_: Optional[Annotated[ObjectId, PyObjectId]] = Field(None, alias="_id")
    experiment_id: str
    part: int
    start_date: datetime
    end_date: datetime
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExperimentPartMappingModel(BaseModel):
    experiment_id: int
    parts: List[int]
    instrument_name: str


class ShotnumConverterRange(BaseModel):
    opposite_range_fields: ClassVar[Dict[str, str]] = {"from": "min_", "to": "max_"}

    min_: Union[int, datetime] = Field(alias="min")
    max_: Union[int, datetime] = Field(alias="max")

    @field_validator("max_")
    def validate_min_max(
        cls,  # noqa: N805
        value,
        values,
    ) -> Union[int, datetime]:
        if value < values.data["min_"]:
            raise ModelError("max cannot be less than min value")
        else:
            return value


class DateConverterRange(BaseModel):
    opposite_range_fields: ClassVar[Dict[str, str]] = {"min": "from_", "max": "to"}

    from_: Union[int, datetime] = Field(alias="from")
    to: Union[int, datetime]

    @field_validator("to")
    def validate_min_max(
        cls,  # noqa: N805
        value,
        values,
    ) -> Union[int, datetime]:
        if value < values.data["from_"]:
            raise ModelError("to cannot be less than from value")
        else:
            return value


class UserSessionModel(BaseModel):
    id_: Optional[Annotated[ObjectId, PyObjectId]] = Field(None, alias="_id")
    username: str
    name: str
    summary: str
    timestamp: datetime
    auto_saved: bool
    session: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True)


class UserSessionListModel(UserSessionModel):
    # Make fields optional that aren't needed in the session list and exclude them from
    # displaying on output
    username: Optional[str] = Field(None, exclude=True)
    session: Optional[Dict[str, Any]] = Field(None, exclude=True)
