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
