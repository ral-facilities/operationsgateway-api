from datetime import datetime
from enum import StrEnum
from typing import Any, Callable, ClassVar, Dict, List, Literal, Optional, Union

from bson.objectid import ObjectId
import numpy as np
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
    StringConstraints,
)
from pydantic_core import core_schema
from typing_extensions import Annotated

from operationsgateway_api.src.exceptions import ChannelManifestError, ModelError


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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


Id = Optional[Annotated[ObjectId, PyObjectId]]
default_id = Field(None, alias="_id")
default_exclude_field = Field(None, exclude=True)


class ChannelDtype(StrEnum):
    IMAGE = "image"
    FLOAT_IMAGE = "float_image"
    WAVEFORM = "waveform"
    VECTOR = "vector"
    SCALAR = "scalar"


class ImageModel(BaseModel):
    path: Optional[Union[str, Any]]
    data: Optional[Union[np.ndarray, Any]]
    bit_depth: Optional[Union[int, Any]] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class FloatImageModel(BaseModel):
    path: str | Any | None
    data: np.ndarray | Any | None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class WaveformModel(BaseModel):
    # Path is optional as we need it when ingesting waveforms (so we know where to store
    # it) but don't want to display it when a user is retrieving a waveform. Setting
    # `exclude=True` inside `Field()` ensures it's not displayed when returned as a
    # response
    path: Optional[str] = default_exclude_field
    x: Optional[Union[List[float], Any]]
    y: Optional[Union[List[float], Any]]
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("x", "y", mode="before")
    def encode_values(cls, value):  # noqa: N805
        if isinstance(value, np.ndarray):
            return list(value)
        else:
            return value


class VectorModel(BaseModel):
    path: str | Any | None = default_exclude_field
    data: list[float] | Any | None

    @field_validator("data", mode="before")
    def validate_data(cls, value):  # noqa: N805
        if isinstance(value, np.ndarray):
            return list(value)
        else:
            return value


class ImageChannelMetadataModel(BaseModel):
    channel_dtype: Literal[ChannelDtype.IMAGE] | Any | None = ChannelDtype.IMAGE
    exposure_time_s: Optional[Union[float, Any]] = None
    gain: Optional[Union[float, Any]] = None
    x_pixel_size: Optional[Union[float, Any]] = None
    x_pixel_units: Optional[Union[str, Any]] = None
    y_pixel_size: Optional[Union[float, Any]] = None
    y_pixel_units: Optional[Union[str, Any]] = None
    bit_depth: Optional[Union[int, Any]] = None

    @field_validator("bit_depth")
    @classmethod
    def validate_bit_depth(cls, bit_depth: "int | Any | None") -> "int | Any | None":
        """
        Ensure that we do not attempt to persist a np.integer by the use of Any.
        While the value from the hdf5 file will (at time of writing) be this type, it
        cannot be sent to Mongo in the model_dump as it is not a valid JSON type.

        Oddly, this only needs to be done for integers - floats behave as expected, and
        Pydantic casts np.floating to float upon __init__.

        Args:
            bit_depth (int | Any | None): Value for bit depth, possible a np.integer

        Returns:
            int | Any | None: Value for bit depth, definitely not a np.integer
        """
        if isinstance(bit_depth, np.integer):
            return int(bit_depth)
        else:
            return bit_depth


class ImageChannelModel(BaseModel):
    metadata: ImageChannelMetadataModel
    image_path: Optional[Union[str, Any]]
    thumbnail: Optional[Union[bytes, Any]] = None


class FloatImageChannelMetadataModel(BaseModel):
    channel_dtype: Literal[ChannelDtype.FLOAT_IMAGE] | Any | None = (
        ChannelDtype.FLOAT_IMAGE
    )
    x_pixel_size: float | Any | None = None
    x_pixel_units: str | Any | None = None
    y_pixel_size: float | Any | None = None
    y_pixel_units: str | Any | None = None


class FloatImageChannelModel(BaseModel):
    metadata: FloatImageChannelMetadataModel
    image_path: str | Any | None
    thumbnail: bytes | Any | None = None


class ScalarChannelMetadataModel(BaseModel):
    channel_dtype: Literal[ChannelDtype.SCALAR] | Any | None = ChannelDtype.SCALAR
    units: Optional[Union[str, Any]] = None


class ScalarChannelModel(BaseModel):
    metadata: ScalarChannelMetadataModel
    data: Optional[Union[int, float, str]]


class WaveformChannelMetadataModel(BaseModel):
    channel_dtype: Literal[ChannelDtype.WAVEFORM] | Any | None = ChannelDtype.WAVEFORM
    x_units: Optional[Union[str, Any]] = None
    y_units: Optional[Union[str, Any]] = None


class WaveformChannelModel(BaseModel):
    metadata: WaveformChannelMetadataModel
    thumbnail: Optional[Union[bytes, Any]] = None
    waveform_path: Optional[Union[str, Any]]


class VectorChannelMetadataModel(BaseModel):
    channel_dtype: Literal[ChannelDtype.VECTOR] | Any | None = ChannelDtype.VECTOR
    units: str | Any | None = None
    labels: list[str] | Any | None = None

    @field_validator("labels", mode="before")
    def validate_labels(cls, value):  # noqa: N805
        if isinstance(value, np.ndarray):
            return list(value)
        else:
            return value


class VectorChannelModel(BaseModel):
    metadata: VectorChannelMetadataModel
    thumbnail: bytes | Any | None = None
    vector_path: str | Any | None = None


class RecordMetadataModel(BaseModel):
    epac_ops_data_version: Optional[Any] = None
    shotnum: Optional[int] = None
    timestamp: Optional[Any] = None
    active_area: Optional[Any] = None
    active_experiment: Optional[Any] = None


class RecordModel(BaseModel):
    id_: str = Field(alias="_id")
    metadata: RecordMetadataModel
    channels: dict[
        str,
        ImageChannelModel
        | FloatImageChannelModel
        | ScalarChannelModel
        | WaveformChannelModel
        | VectorChannelModel,
    ]


class PartialImageChannelModel(ImageChannelModel):
    metadata: ImageChannelMetadataModel | None = None
    image_path: str | None = None
    thumbnail: bytes | None = None


class PartialFloatImageChannelModel(FloatImageChannelModel):
    metadata: ImageChannelMetadataModel | None = None
    image_path: str | None = None
    thumbnail: bytes | None = None


class PartialScalarChannelModel(ScalarChannelModel):
    metadata: ScalarChannelMetadataModel | None = None
    data: int | float | str | None = None


class PartialWaveformChannelModel(WaveformChannelModel):
    metadata: WaveformChannelMetadataModel | None = None
    thumbnail: bytes | None = None
    waveform_path: str | None = None


class PartialVectorChannelModel(VectorChannelModel):
    metadata: VectorChannelMetadataModel | None = None
    thumbnail: bytes | None = None
    vector_path: str | None = None


PartialChannelModel = (
    PartialImageChannelModel
    | PartialFloatImageChannelModel
    | PartialScalarChannelModel
    | PartialWaveformChannelModel
    | PartialVectorChannelModel
)
PartialChannels = dict[str, PartialChannelModel]


class PartialRecordModel(RecordModel):
    metadata: RecordMetadataModel | None = None
    channels: PartialChannels | None = None


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
    # Email needs to be optional so local login can work
    email: Optional[EmailStr] = None


class UpdateUserModel(BaseModel):
    username: str = Field(alias="_id")
    updated_password: Optional[str] = None
    add_authorised_routes: Optional[List[str]] = None
    remove_authorised_routes: Optional[List[str]] = None


class ChannelModel(BaseModel):
    # Field names where modifications to the data cannot be made
    protected_fields: ClassVar[List[str]] = ["type_", "units"]

    name: str
    path: str
    type_: ChannelDtype | None = Field(
        None,
        alias="type",
    )

    # Should the value be displayed as it is stored or be shown in x10^n format
    notation: Optional[Literal["scientific", "normal"]] = None
    # Number of significant figures used to display the value
    precision: Optional[int] = None
    units: Optional[str] = None
    historical: Optional[bool] = None

    x_units: Optional[str] = None
    y_units: Optional[str] = None

    labels: list[str] | None = None

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

    @field_validator("labels")
    def check_vector_channel(cls, v, values):  # noqa: N805
        if not values.data["type_"] == ChannelDtype.VECTOR:
            raise ChannelManifestError(
                "Only vector channels should contain vector channel metadata."
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
    id_: Id = default_id
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
    id_: Id = default_id
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
    username: Optional[str] = default_exclude_field
    session: Optional[Dict[str, Any]] = default_exclude_field


class FavouriteFilterModel(BaseModel):
    id_: Id = default_id
    name: str
    filter: str  # noqa: A003


class Function(BaseModel):
    name: NonEmptyString
    expression: NonEmptyString


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"


class MaintenanceModel(BaseModel):
    show: bool
    message: str


class ScheduledMaintenanceModel(MaintenanceModel):
    severity: Severity


class IngestionResponse(BaseModel):
    accepted_channels: List[str] = Field(
        ...,
        description="A List of channel names successfully accepted and ingested.",
    )
    rejected_channels: Dict[str, Union[str, List[str]]] = Field(
        ...,
        description=("Dictionary mapping channel names to rejection reasons."),
    )
    warnings: Optional[List[str]] = Field(
        default=[],
        description="List of non-critical issues encountered during ingestion, "
        "currently around EPAC data version",
    )


class SubmitHDFResponse(BaseModel):
    message: str = Field(
        ...,
        description="Indicates whether a HDF file was added, updated or rejected.",
    )
    response: IngestionResponse = Field(
        ...,
        description="Detailed information about which channels were "
        "accepted, rejected, and whether there are any warnings.",
    )
