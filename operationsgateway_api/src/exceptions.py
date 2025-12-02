class ApiError(Exception):
    def __init__(self, msg: str, status_code: int = 500, *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = status_code


class RejectFileError(ApiError):
    def __init__(self, msg="HDF file rejected", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 400


class RejectRecordError(ApiError):
    def __init__(self, msg="HDF file record rejected", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 400


class DuplicateSessionError(ApiError):
    def __init__(self, msg="Database error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 400


class DatabaseError(ApiError):
    def __init__(self, msg="Database error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 500


class AuthServerError(ApiError):
    def __init__(self, msg="Authentication server error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 500


class UnauthorisedError(ApiError):
    def __init__(
        self,
        msg="You are not authorised to access this service",
        *args,
        **kwargs,
    ):
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


class ChannelManifestError(ApiError):
    def __init__(self, msg="Channel manifest error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 400


class ChannelSummaryError(ApiError):
    def __init__(self, msg="Channel summary error", *args, **kwargs):
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


class MissingAttributeError(ApiError):
    def __init__(self, msg="No such attribute in database", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 404


class QueryParameterError(ApiError):
    def __init__(self, msg="Problem with query parameter input", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 400


class EchoS3Error(ApiError):
    def __init__(self, msg="Echo S3 error", status_code: int = 500, *args, **kwargs):
        super().__init__(msg, status_code, *args, **kwargs)


class ExperimentDetailsError(ApiError):
    def __init__(self, msg="Error during handling of experiments", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 500


class FunctionParseError(ApiError):
    def __init__(self, msg="Problem with function syntax", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 400


class ExportError(ApiError):
    def __init__(self, msg="Error during creation of export file", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 400


class UserError(ApiError):
    def __init__(self, msg="User error", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 400


class InvalidJWTError(UserError):
    def __init__(self, msg="Invalid OIDC id_token", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 403  # forbidden


class OidcProviderNotFoundError(AuthServerError):
    def __init__(self, msg="Unknown OIDC provider", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.status_code = 404  # not found
