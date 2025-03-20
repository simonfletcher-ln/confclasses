from io import StringIO
from confclasses import confclass, load_config, ConfclassesLoadingError, save_config
from confclasses_comments import save_config as save_config_comments
import pytest

@pytest.fixture
def test_config():
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
    class TestConfig:
        nested: NestedConfig
        field3: int = 42
        """ test document for field 3 """
        hashed_field1: list = ["test", "items"]
        hashed_field2: dict = {"key1": "value1"}
        hashed_field4: RepeatingConfig = RepeatingConfig(test="base")
    
    return TestConfig

@pytest.fixture
def test_config_yaml():
    return """nested:
  field1: foo
  field2: bar
  hashed_field3:
    test: nested
    default1: 123
field3: 42
hashed_field1:
- test
- items
hashed_field2:
  key1: value1
hashed_field4:
  test: base
  default1: 123
"""

@pytest.fixture
def test_config_yaml_comments():
    return """
nested:

# ### field1 ###
# type: String
  field1: foo

# ### field2 ###
# type: String
# test document for field 2
  field2: bar

  hashed_field3:

# ### test ###
# type: String
    test: nested

# ### default1 ###
# type: Integer
    default1: 123

# ### field3 ###
# type: Integer
# test document for field 3
field3: 42

# ### hashed_field1 ###
# type: list
hashed_field1:
- test
- items

# ### hashed_field2 ###
# type: dict
hashed_field2:
  key1: value1

hashed_field4:

# ### test ###
# type: String
  test: base

# ### default1 ###
# type: Integer
  default1: 123
"""

def test_wrapper(test_config):
    """ Other tests cover this but if this test fails it's obviously the wrapper that broke """
    pass

def test_error_pre_load(test_config):
    """ We want to raise exceptions if config is accessed before its loaded """
    conf = test_config()
    with pytest.raises(ConfclassesLoadingError):
        conf.field3
    with pytest.raises(ConfclassesLoadingError):
        conf.nested.field1

def test_unsafe(test_config):
    """ in the case safe=False, we do the opposit of the above test """
    @confclass(safe=False)
    class UnsafeTestConfig():
        nested_safe: test_config # type: ignore
        field: int = 22
    
    conf = UnsafeTestConfig()
    _ = conf.field

    with pytest.raises(AttributeError):
        _ = conf.nested_safe.field3
    
    load_config(conf, "")

def test_hashing(test_config):
    """ Make sure hashed fields do not polute """
    conf1 = test_config()
    conf2 = test_config()
    load_config(conf1, "")
    load_config(conf2, "")
    assert len(conf1.hashed_field1) == 2
    conf1.hashed_field1.append("new")
    assert len(conf2.hashed_field1) == 2

def test_init_defaults(test_config):
    """ Make sure if nested has defaults passed in from parent definition """
    conf = test_config()

    load_config(conf, "")
    assert conf.hashed_field4.test == "base"
    assert conf.nested.hashed_field3.test == "nested"

def test_defaults(test_config):
    """ In development nested defaults got messy, testing that """
    conf = test_config()

    load_config(conf, "")
    assert conf.field3 == 42
    assert conf.nested.field1 == "foo"

def test_load(test_config):
    conf = test_config()

    load_config(conf, """field3: 59
nested:
  field1: "test"
""")
    assert conf.field3 == 59
    assert conf.nested.field1 == "test"
    assert conf.nested.field2 == "bar"

def test_save(test_config, test_config_yaml):
    conf = test_config()
    load_config(conf, "")
    assert save_config(conf) == test_config_yaml

def test_save_comments(test_config, test_config_yaml_comments):
    conf = test_config()
    load_config(conf, "")
    stream = StringIO()
    save_config_comments(conf, stream)
    print(stream.getvalue())
    assert stream.getvalue() == test_config_yaml_comments