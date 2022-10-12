class ApiError(Exception):
    # default status code if not overridden
    status_code = 500


class DatabaseError(ApiError):
    def __init__(self, msg="Database error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 500


class AuthServerError(ApiError):
    def __init__(self, msg="Authentication server error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 500


class UnauthorisedError(ApiError):
    def __init__(self, msg="User not authorised", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 401


class ForbiddenError(ApiError):
    def __init__(self, msg="No access rights", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 403


class HDFDataExtractionError(ApiError):
    def __init__(self, msg="HDF ingestion error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 400


class ModelError(ApiError):
    def __init__(self, msg="Model creation error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 400


class ImageError(ApiError):
    def __init__(self, msg="Image error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 500


class RecordError(ApiError):
    def __init__(self, msg="Record error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 500


class MissingDocumentError(ApiError):
    def __init__(self, msg="No such document in database", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 404
