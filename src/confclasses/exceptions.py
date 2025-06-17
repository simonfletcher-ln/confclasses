class ConfclassesAttributeError(Exception):
    pass

class ConfclassesSetupError(Exception):
    pass

class ConfclassesLoadingError(Exception):
    """ Raised when loading configuration fails """
    pass

class ConfclassesMissingValueError(ConfclassesLoadingError):
    """ Raised when a required value is missing from defaults or loaded configuration """
    pass