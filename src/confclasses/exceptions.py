from typing import List


class ConfclassesAttributeError(Exception):
    pass

class ConfclassesSetupError(Exception):
    pass

class ConfclassesLoadingError(Exception):
    """ Raised when loading configuration fails """
    pass

class ConfclassesMissingValueError(ConfclassesLoadingError):
    """ Raised when a required value is missing from defaults or loaded configuration """
    missing: List[str]

    def __init__(self, *args, missing: List[str] = None, **kwargs):
        self.missing = missing
        super().__init__(*args, **kwargs)