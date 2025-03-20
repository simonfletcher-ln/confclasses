import dataclasses
import yaml
import inspect

__version__ = "0.0.1"

__all__ = [
    'configclass',
    'load_config',
    'save_config',
    'is_confclass',
    'fields'
]

import logging
logger = logging.getLogger(__name__)

class ConfclassesLoadingError(Exception):
    pass

fields = dataclasses.fields

def confclass(cls=None, /, *, safe=True):
    """
    A simplified version of dataclass decorator, allowing shorthand notation.

    Args:
        safe (bool): If we should stop access to read values before load_config is called. Be careful with this.

    Example:
    ```python
        @configclass
        class MyConfig:
            nested: NestedConfig
            field: int = 42
            hashed_field: list = ['item']
    ```
    """
    def wrap(cls):
        # loop the fields
        for name, type in inspect.get_annotations(cls).items():
            default = getattr(cls, name, dataclasses.MISSING)
            # auto create any nested configclasses
            if is_confclass(default) and default is dataclasses.MISSING:
                setattr(cls, name, dataclasses.field(default_factory=lambda: type()))
            # auto create a default_factory if needed
            elif default is not dataclasses.MISSING and default.__class__.__hash__ is None:
                if is_confclass(default):
                    setattr(cls, name, dataclasses.field(default_factory=lambda: default))
                else:
                    setattr(cls, name, dataclasses.field(default_factory=default.copy))

        # save the dataclass init for later
        cls = dataclasses.dataclass(cls)
        setattr(cls, "__dataclass_init__", cls.__init__)
        setattr(cls, "__init__", _init)
        setattr(cls, _LOADED, False)
        if safe:
            setattr(cls, "__getattribute__", _getattribute)

        return cls

    if cls is None:
        return wrap
    
    return wrap(cls)


_LOADED = "__CONFIGCLASSES_LOADED__"
def _getattribute(config, name):
    """
    The purpose for this override function is to block lookups before it is loaded.

    """
    if name.startswith('__'):
        return object.__getattribute__(config, name)
    
    if not object.__getattribute__(config, _LOADED):
        raise ConfclassesLoadingError(f"accessing config '{name}' before loaded")
    else:
        setattr(config, "__getattribute__", super(type(config)).__getattribute__)
        return object.__getattribute__(config, name)

def _init(config, *args, **kwargs):
    config.__confclass_args__ = args
    config.__confclass_kwargs__ = kwargs

def load_config(config, yaml_str):
    """
    Load configuration from a YAML string into a given config object.

    Args:
        config (object): The configuration object to populate.
        yaml_str (str): The YAML string containing the configuration data.

    """
    obj = yaml.safe_load(yaml_str)
    if obj is None:
        obj = {}
    if obj is list:
        raise ValueError("Invalid config")
    
    from_dict(config, obj)


def save_config(config) -> str:
    """
    Convers a given config object into a yaml string

    Args:
        config (object): the config object
        comments (bool): if the yaml should contain comments
    """

    return yaml.safe_dump(dataclasses.asdict(config), sort_keys=False)

def is_confclass(obj):
    """
    Check if the given object is a confclass.
    
    Args:
        obj (object|type): object or type to check
    Returns:
        bool: True if the object is a confclass, False otherwise.
    """
    cls = obj if isinstance(obj, type) else type(obj)
    return hasattr(cls, _LOADED)

def from_dict(config: object, values: dict, crumbs: list=[]):
    """
    Recursively populates a dataclass instance with values from a dictionary.

    Args:
        config (object): The dataclass instance to populate.
        values (dict): A dictionary containing the values to populate the dataclass with.
        crumbs (list, optional): A list used to track the hierarchy of nested dataclasses.
    """

    kwargs = {}
    for field in dataclasses.fields(config):
        if is_confclass(field.type):
            if field.default_factory is not dataclasses.MISSING:
                kwargs[field.name] = field.default_factory()
            else:
                kwargs[field.name] = field.type()

            from_dict(kwargs[field.name], values.get(field.name, {}), crumbs + [field.name])
        elif field.name in values:
            kwargs[field.name] = values[field.name]

    # this is just for logging, doesn't serve any function
    for name, value in values.items():
        if name not in kwargs:
            logger.info(f"unused config {'.'.join(crumbs + [name])} = {value}")

    config.__dataclass_init__(
        *config.__confclass_args__,
        **config.__confclass_kwargs__,
        **kwargs
    )
    setattr(config, _LOADED, True)
