# Confclasses

Create dataclass style classes that can be used for configuration of a python tool. The idea is to handle loading/saving 
the config from files while allowing simpler IDE usage with the config. We dont need 90% of the features in dataclasses, 
so we make the api easier.


The module is designed to have a global config object that is instantiated at the start and then loaded dynamically
later. This is why the dataclass __init__ is pushed aside and we run it manually later.

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

Use it elsewhere in the project
```python
from confclasses import load_config
from config import config

def main():
    with open('conf.yaml', 'r') as f:
        load_config(config, f.read())
    
    print(config.field3)
```