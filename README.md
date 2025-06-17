# Confclasses

Create dataclass-style classes that can be used for configuring a Python tool. The idea is to handle loading and saving the config from files while allowing simpler IDE usage with the config. We don't need 90% of the features in dataclasses, so we make the API easier.

The module is designed to have a global config object that is instantiated at the start and then loaded dynamically later. Please see the common usage section for an example.

`confclasses_comments` is also shipped with this tool. It uses `ruamel.yaml` to add comments and `ast` to get the "docstring" of the annotations (fields) in the config classes.

## Common usage
Create a config.py to store the config.

```python
# config.py
@confclass
class RepeatingConfig:
    test: str
    default1: int = 123
    
@confclass
class NestedConfig:
    field1: str = "foo"
    field2: str = "bar"
    """ test document for field 2 """
    hashed_field3: RepeatingConfig = RepeatingConfig(test="nested")

@confclass
class ExampleConfig:
    nested: NestedConfig
    field3: int = 42
    """ test document for field 3 """
    hashed_field1: list = ["test", "items"]
    hashed_field2: dict = {"key1": "value1"}
    hashed_field4: RepeatingConfig = RepeatingConfig(test="base")

config = ExampleConfig()
```

Loading it at the start
```python
# main.py
from confclasses import load_config
from config import config
from .example_module import example_function

def main():
    with open('conf.yaml', 'r') as f:
        load_config(config, f.read())
    
    example_function()
```

In the `example_module`
```python
# example_module.py
from config import config

def example_function():
    print(config.field3)
```

## Planned changes
- [ ] XDG support
- [x] Move comments code into base file
- [ ] Type checking
- [ ] Tests in pipelines
- [ ] Contribution guide
- [x] Scalars mapped to confclass
- [x] remove PyYAML
