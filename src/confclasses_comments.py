import ast
import dataclasses
import functools
import inspect
from confclasses import is_confclass
from ruamel.yaml import YAML, CommentedMap

@functools.cache
def get_docstrings(cls):
    """
    Returns a mapping of attribute name to docstring, uses ast and inspect. I have
    used the same documenting standards that most IDEs support rather than a true
    python approach. This can be reworked if a proper standard emerges from python.

    Args:
        obj (object|type): the object or type to inspect
    """
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
        if isinstance(item, ast.Expr): # If the docstring
            if isinstance(body[i - 1], ast.AnnAssign): # If previous line was an annotation
                mapping[body[i - 1].target.id] = item.value.value
    return mapping

TYPE_MAPPING = {
    str: "String",
    int: "Integer",
    float: "Float",
    bool: "Bool",
}

def add_comments(data, cls):
    # Now we use ast and inspect to get the comments out
    docs = get_docstrings(cls)
    for field_info in dataclasses.fields(cls):
        # Deal with recursion first
        if is_confclass(field_info.type):
            add_comments(data[field_info.name], field_info.type)
            comment_text = "" # this is a simple way to force an empty new line
        else:
            comment_text = f"""
### {field_info.name} ###
type: {TYPE_MAPPING.get(field_info.type, field_info.type.__name__)}
{docs.get(field_info.name, "").strip()}"""
            
        data.yaml_set_comment_before_after_key(field_info.name, before=comment_text)


def save_config(config, stream):
    yaml = YAML()
    yaml.default_flow_style = False
    data = dataclasses.asdict(config, dict_factory=CommentedMap)
    add_comments(data, type(config))
    yaml.dump(data, stream)
