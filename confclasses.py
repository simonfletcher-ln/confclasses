import dataclasses
# Yes, we use both yaml and ruamel, this is because for loading we dont want all those features
from ruamel.yaml import YAML, CommentedMap
import yaml
import inspect
import functools
import ast
from io import StringIO


__all__ = [
    'configclass',
    'load_config',
    'save_config',
    'is_confclass'
]

import logging
logger = logging.getLogger(__name__)

class ConfclassesLoadingError(Exception):
    pass

def confclass(cls=None):
    """
    A simplified version of dataclass decorator, allowing shorthand notation.

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
                setattr(cls, name, dataclasses.field(default_factory=_copy(default)))

        # save the dataclass init for later
        cls = dataclasses.dataclass(cls)
        setattr(cls, "__dataclass_init__", cls.__init__)
        setattr(cls, "__init__", _init)
        setattr(cls, _LOADED, False)
        setattr(cls, "__getattribute__", _getattribute)

        return cls

    if cls is None:
        return wrap
    
    return wrap(cls)


def _copy(obj):
    def factory():
        if is_confclass(obj):
            return obj.__class__(*obj.__confclass_args__, **obj.__confclass_kwargs__)
        else:
            return obj.copy()
    return factory

_LOADED = "__CONFIGCLASSES_LOADED__"
def _getattribute(config, name):
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

@functools.cache
def get_docstrings(cls):
    """
    Returns a mapping of attribute name to docstring, uses ast and inspect. I have
    used the same documenting standards that most IDEs support rather than a true
    python approach. This can be reworked but a proper standard emerges from python.

    Args:
        obj (object|type): the object or type to inspect
    """
    print(f"inspecting {cls}")
    src = inspect.getsource(cls)
    try:
        tree = ast.parse(src)
    except IndentationError:
        src = inspect.cleandoc(src)
        tree = ast.parse(src)
    
    body = tree.body[0].body
    mapping = {}
    for i, item in enumerate(body):
        if i == 0:
            continue
        if isinstance(item, ast.Expr):
            if isinstance(body[i - 1], ast.AnnAssign):
                mapping[body[i - 1].target.id] = item.value.value
    return mapping

TYPE_MAPPING = {
    str: "Text",
    int: "Number",
    float: "Decimal",
    bool: "Yes/No",
}

def add_comments(data, cls, indent=0):
    # Now we use ast and inspect to get the comments out
    docs = get_docstrings(cls)
    for field_info in dataclasses.fields(cls):
        # Deal with recursion first
        if is_confclass(field_info.type):
            add_comments(data[field_info.name], field_info.type, indent+2)
        comment_text = f"""
=== {field_info.name} ===
type: {TYPE_MAPPING.get(field_info.type, field_info.type.__name__)}
{docs.get(field_info.name, "").strip()}"""
        
        data.yaml_set_comment_before_after_key(field_info.name, indent=indent, before=comment_text)


def save_config(config, comments: bool = False) -> str:
    """
    Convers a given config object into a yaml string

    Args:
        config (object): the config object
        comments (bool): if the yaml should contain comments
    """
    yaml = YAML()
    yaml.default_flow_style = False
    data = dataclasses.asdict(config, dict_factory=CommentedMap)
    if comments:
        add_comments(data, type(config))
    stream = StringIO()
    yaml.dump(data, stream)
    out = stream.getvalue()
    stream.close()
    return out

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
            logger.info(f"unused config {".".join(crumbs + [name])} = {value}")

    config.__dataclass_init__(
        *config.__confclass_args__,
        **config.__confclass_kwargs__,
        **kwargs
    )
    setattr(config, _LOADED, True)
