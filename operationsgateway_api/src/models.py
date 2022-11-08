from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


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


class Record(BaseModel):
    id_: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    # title: Optional[str]

    """
    #@root_validator(pre=True)
    @classmethod
    def build_data(cls, mongo_data):
        pydantic_record_field_names = cls.__fields__

        for key, value in mongo_data.items():
            if key not in pydantic_record_field_names:
                setattr(cls, key, value)

        return cls
    """

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class LoginDetails(BaseModel):
    username: str
    password: str


class AccessToken(BaseModel):
    token: str


class UserModel(BaseModel):
    username: str = Field(alias="_id")
    sha256_password: Optional[str]
    auth_type: str
    authorised_routes: Optional[List[str]]


class RecordsQueryParams:
    filter_: dict
    skip: int
    limit: int
    order: Optional[List[str]]
    projection: Optional[List[str]]
