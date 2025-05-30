import dataclasses
from io import StringIO
from ruamel.yaml import YAML
from ruamel.yaml.comments import TaggedScalar, CommentedSeq, CommentedMap
import inspect
from typing import get_args, get_origin

__version__ = "0.0.1"

__all__ = [
    'confclass',
    'load_config',
    'save_config',
    'is_confclass',
    'fields',
    'tag'
]

_LOADED = "__CONFIGCLASSES_LOADED__"
_TAGS = "__CONFIGCLASSES_TAGS__"
_SCALAR = "__CONFIGCLASSES_SCALAR__"

import logging
logger = logging.getLogger(__name__)

class ConfclassesLoadingError(Exception):
    pass

fields = dataclasses.fields

def confclass(cls=None, /, *, safe=True, scalar=False):
    """
    A simplified version of dataclass decorator, allowing shorthand notation.

    Args:
        safe (bool): If we should stop access to read values before load_config is called. Be careful with this.
        scalar (bool): If the class is a scalar. This is used in combination with the tag decorator.

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
        setattr(cls, _SCALAR, scalar)
        setattr(cls, _LOADED, False)
        if safe:
            setattr(cls, "__getattribute__", _getattribute)

        return cls

    if cls is None:
        return wrap
    
    return wrap(cls)

def tag(name, /, *, target=None, flag=False):
    """
    A decorator to define tags for a confclass. 

    Args:
        name (str): the name of the tag
        attr (str, optional): the name of the attribute to add the tag to. Defaults to None.
        flag (bool, optional): if the tag is a flag. Defaults to False.
    """
    def wrap(cls):
        if not hasattr(cls, _TAGS):
            setattr(cls, _TAGS, [])
        getattr(cls, _TAGS).append((name, target, flag))
        return cls
    
    return wrap

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

def load_config(config, stream):
    """
    Load configuration from a YAML string into a given config object.

    Args:
        config (confclass): The configuration object to populate.
        yaml_str (str): The YAML string containing the configuration data.

    """
    yaml = YAML()
    yaml.default_flow_style = False

    obj = yaml.load(stream)
    if obj is None:
        obj = {}
    if obj is list:
        raise ValueError("Invalid config")
    
    from_dict(config, obj)


def save_config(config, stream=None, comments=False) -> str:
    """
    Convers a given config object into a yaml string

    Args:
        config (confclass): the config object
        comments (bool): if the yaml should contain comments
    """
    yaml = YAML()
    yaml.default_flow_style = False

    return_yaml = False
    if stream is None:
        return_yaml = True
        stream = StringIO()
    
    data = dataclasses.asdict(config, dict_factory=CommentedMap)
    if comments:
        from confclasses_comments import add_comments
        add_comments(data, type(config))
        
    yaml.dump(data, stream=stream)
    if return_yaml:
        return stream.getvalue()

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
    

def tagged_scalar_to_tupple(tagged_scalar):
    if isinstance(tagged_scalar, TaggedScalar):
        return (tagged_scalar.value, str(tagged_scalar.tag))
    return (tagged_scalar,None)

def from_dict(config: object, values: dict, crumbs: list=[]):
    """
    Recursively populates a dataclass instance with values from a dictionary.

    Args:
        config (confclass): The dataclass instance to populate.
        values (dict): A dictionary containing the values to populate the dataclass with.
        crumbs (list, optional): A list used to track the hierarchy of nested dataclasses.
    """
    is_scalar = getattr(config, _SCALAR)
    logger.debug(f"from_dict {crumbs}:{is_scalar}")
    
    args = []
    kwargs = {}

    if is_scalar:
        value, tag = tagged_scalar_to_tupple(values)
        if tag is not None:
            for name, target, flag in getattr(config, _TAGS, []):
                if tag.startswith("!"):
                    tag = tag[1:]
                
                if tag == name:
                    if target is None:
                        target = name
                    if flag:
                        kwargs[target] = True
                    else:
                        kwargs[target] = name
        args = [value]
    else:
        for field in dataclasses.fields(config):
            # if the field is a confclass, we create a new object and merge
            # the values into it
            if is_confclass(field.type):
                if field.default_factory is not dataclasses.MISSING:
                    kwargs[field.name] = field.default_factory()
                else:
                    kwargs[field.name] = field.type()
                
                from_dict(kwargs[field.name], values.get(field.name, {}), crumbs + [field.name])
                continue

            # lists can contain anything, so we need to check all elements in it
            if get_origin(field.type) is list:
                if field.name in values and type(values[field.name]) is not CommentedSeq:
                    raise ValueError(f"Invalid type at {'.'.join(crumbs + [field.name])}, expected {field.type} got {type(values[field.name])}")

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
                            values[field.name][i] = tagged_scalar_to_tupple(item)[0] # strip tags if were not a confclass
                            if obj_type is not type(values[field.name][i]):
                                raise ValueError(f"Invalid type in {'.'.join(crumbs + [field.name, str(i)])} for {field.name}, expected {obj_type} got {type(values[field.name][i])}")
                        kwargs[field.name] = values[field.name]
                        continue

            # for anything else, we validate the type and assign the value
            if field.name in values:
                if field.type is not type(values[field.name]):
                    raise ValueError(f"Invalid type in {'.'.join(crumbs + [field.name])} for {field.name}, expected {field.type} got {type(values[field.name])}")
                kwargs[field.name] = tagged_scalar_to_tupple(values[field.name])[0]

        # this is just for logging, doesn't serve any function
        for name, value in values.items():
            if name not in kwargs:
                logger.info(f"unused config {'.'.join(crumbs + [name])} = {value}")

    config.__dataclass_init__(
        *config.__confclass_args__,
        *args,
        **config.__confclass_kwargs__,
        **kwargs
    )
    setattr(config, _LOADED, True)
