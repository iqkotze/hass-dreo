"""Exceptions raised by PyDreo."""


class DreoCommandRejectedError(Exception):
    """The Dreo server rejected a command (e.g. error 500003, "instruction validate failed")."""


class DreoInvalidValueError(ValueError):
    """A setting was given a value outside its valid range."""

    def __init__(self, name: str, value, valid_range: tuple | None = None):
        self.name = name
        self.value = value
        self.valid_range = valid_range
        if valid_range is None:
            message = f"{name}: value {value} cannot be set (not supported by this device)"
        else:
            message = f"{name}: value {value} is not in the acceptable range {valid_range}"
        super().__init__(message)
