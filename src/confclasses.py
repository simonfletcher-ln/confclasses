import dataclasses
import yaml
import inspect
from typing import get_origin, get_args

__version__ = "0.0.1"

__all__ = [
    'configclass',
    'load_config',
    'save_config',
    'is_confclass',
    'fields',
    'ConfclassesAttributeError'
]

_LOADED = "__CONFIGCLASSES_LOADED__"
_SCALAR = "__CONFIGCLASSES_SCALAR__"

import logging
logger = logging.getLogger(__name__)

class ConfclassesAttributeError(Exception):
    pass

class ConfclassesSetupError(Exception):
    pass

class ConfclassesLoadingError(Exception):
    pass

fields = dataclasses.fields

def confclass(cls=None, /, *, safe=True, if_scalar=None):
    """
    A simplified version of dataclass decorator, allowing shorthand notation.

    Args:
        safe (bool): If we should stop access to read values before load_config is called. Be careful with this.
        if_scalar (str): If config value is a scalar, we will use default values for all fields except this one. This field will be filled with the scalar value.

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

        if_scalar_found = False
        if_scalar_defaults = True

        # loop the fields
        for name, f_type in inspect.get_annotations(cls).items():
            default = getattr(cls, name, dataclasses.MISSING)
            # auto create any nested configclasses
            if is_confclass(f_type) and default is dataclasses.MISSING:
                setattr(cls, name, dataclasses.field(default_factory=f_type))
            # auto create a default_factory if needed
            elif default is not dataclasses.MISSING and default.__class__.__hash__ is None:
                if is_confclass(default):
                    setattr(cls, name, dataclasses.field(default_factory=lambda: default))
                else:
                    setattr(cls, name, dataclasses.field(default_factory=default.copy))
            if if_scalar is not None:
                if is_confclass(f_type):
                    raise ConfclassesSetupError(f"if_scalar is set, cannot contain a nested confclass in {cls.__name__}")
                if name == if_scalar:
                    if_scalar_found = True
                else:
                    if default is dataclasses.MISSING:
                        if_scalar_defaults = False

        # save the dataclass init for later
        cls = dataclasses.dataclass(cls)
        setattr(cls, "__dataclass_init__", cls.__init__)
        setattr(cls, "__init__", _init)
        setattr(cls, _LOADED, False)
        if safe:
            setattr(cls, "__getattribute__", _getattribute)
            
        if if_scalar is not None:
            if not if_scalar_defaults:
                raise ConfclassesSetupError(f"if_scalar is set, all other fields must have defaults in {cls.__name__}")
            if if_scalar_found:
                setattr(cls, _SCALAR, if_scalar)
            else:
                raise ConfclassesSetupError(f"if_scalar field {if_scalar} not found in {cls.__name__}")

        return cls

    if cls is None:
        return wrap
    
    return wrap(cls)


def _getattribute(config, name):
    """
    The purpose for this override function is to block lookups before it is loaded.

    """
    if name.startswith('__'):
        return object.__getattribute__(config, name)
    
    if not object.__getattribute__(config, _LOADED):
        raise ConfclassesAttributeError(f"accessing config '{name}' before loaded")
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
    """

    try:
        obj = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        raise ConfclassesLoadingError(f"Error loading config: {e}")
    
    if obj is None:
        obj = {}
    if type(obj) is not dict:
        raise ConfclassesLoadingError("YAML must be a dictionary")
    
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

def from_dict(config: object, values: dict | str, crumbs: list=None):
    """
    Recursively populates a dataclass instance with values from a dictionary.

    Args:
        config (object): The dataclass instance to populate.
        values (dict): A dictionary containing the values to populate the dataclass with.
        crumbs (list, optional): A list used to track the hierarchy of nested dataclasses.
    """
    if crumbs is None:
        crumbs = ['root']
    
    kwargs = {}
    if isinstance(values, dict):
        for field in dataclasses.fields(config):
            # if the field is a confclass, we create a new object and merge
            # the values into it
            if is_confclass(field.type):
                default_value = values.get(field.name, {})
                if field.default_factory is not dataclasses.MISSING:
                    kwargs[field.name] = field.default_factory()
                elif field.default is not dataclasses.MISSING and hasattr(field.type, _SCALAR):
                    kwargs[field.name] = field.type()
                    default_value = field.default
                else:
                    kwargs[field.name] = field.type()
                
                from_dict(kwargs[field.name], default_value, crumbs + [field.name])
                continue

            # lists can contain anything, so we need to check all elements in it
            if get_origin(field.type) is list:
                # if the field type is a list of confclasses, just assume pass into from_dict.
                obj_type = get_args(field.type)[0]
                if is_confclass(obj_type):
                    if field.name in values:
                        kwargs[field.name] = values[field.name]
                    elif field.default_factory is not dataclasses.MISSING:
                        kwargs[field.name] = field.default_factory()
                    else:
                        kwargs[field.name] = []
                    
                    # after we have a list, we need to convert them into objects
                    for i, item in enumerate(kwargs[field.name]):
                        new_item = obj_type()
                        from_dict(new_item, item, crumbs + [field.name, str(i)])
                        kwargs[field.name][i] = new_item
                    continue
                else:
                    if field.name in values:
                        for i, item in enumerate(values[field.name]):
                            values[field.name][i] = item
                            if obj_type is not type(values[field.name][i]):
                                raise ValueError(f"Invalid type in {'.'.join(crumbs + [field.name, str(i)])} for {field.name}, expected {obj_type} got {type(values[field.name][i])}")
                        kwargs[field.name] = values[field.name]
                        continue

            # Check for missing required fields
            if field.name not in values and field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
                raise ValueError(
                    f"Missing required config field {'.'.join(crumbs + [field.name])}"
                )
            
            # for anything else, we validate the type and assign the value
            if field.name in values:
                if field.type is not type(values[field.name]):
                    raise ValueError(f"Invalid type in {'.'.join(crumbs + [field.name])} for {field.name}, expected {field.type} got {type(values[field.name])}")
                
                kwargs[field.name] = values[field.name]

        # this is just for logging, doesn't serve any function
        for name, value in values.items():
            if name not in kwargs:
                logger.info(f"unused config {'.'.join(crumbs + [name])} = {value}")
    
    elif isinstance(values, str):
        if hasattr(config, _SCALAR):
            kwargs[getattr(config, _SCALAR)] = values
        else:
            raise ValueError(f"Scalar value {values} found, but if_scalar not set in {config.__class__.__name__}")
    else:
        raise ValueError(f"Invalid type in {'.'.join(crumbs)}, expected dict or str got {type(values)}")
    

    config.__dataclass_init__(
        *config.__confclass_args__,
        **config.__confclass_kwargs__,
        **kwargs
    )
    setattr(config, _LOADED, True)
