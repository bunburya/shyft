class BaseShyftException(Exception):
    """Base class for all Shyft-related exceptions."""
    pass

class ActivityExistsError(BaseShyftException):
    """Activity already exists in database."""
    pass