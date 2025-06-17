from io import StringIO
import pytest

from confclasses import confclass, load, save
from confclasses.exceptions import ConfclassesLoadingError, ConfclassesSetupError, ConfclassesAttributeError, ConfclassesMissingValueError

# These are the old interfaces we're deprecating but they make tests easier
# so we're keeping them around for tests

def load_config(config, yaml):
    stream = StringIO(yaml)
    return load(config, stream)

def save_config(config):
    stream = StringIO()
    save(config, stream)
    return stream.getvalue()

@pytest.fixture
def test_config():
    @confclass
    class RepeatingConfig:
        test: str = "test"
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

    with pytest.raises(ConfclassesAttributeError):
        hasattr(conf, "field3")
    with pytest.raises(ConfclassesAttributeError):
        getattr(conf, "field3")
    with pytest.raises(ConfclassesAttributeError):
        conf.nested.field1

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
    save(conf, stream, comments=True)
    assert stream.getvalue() == test_config_yaml_comments

def test_lists():
    @confclass
    class ListConfigItem:
        name: str

    @confclass
    class ListConfig:
        items: list[ListConfigItem] = []

    conf = ListConfig()
    load_config(conf, """items:
  - name: test1
  - name: test2
""")
    assert len(conf.items) == 2
    assert conf.items[0].name == "test1"
    assert conf.items[1].name == "test2"

def test_scalar():
    @confclass(if_scalar="test")
    class ScalarConfig:
        test: str
        other: int = 42

    conf = ScalarConfig()
    load_config(conf, "test: value")
    assert conf.test == "value"
    assert conf.other == 42

def test_scalar_without_defaults():
    with pytest.raises(ConfclassesSetupError):
        @confclass(if_scalar="test")
        class ScalarConfig:
            test: str
            other: int

def test_scalar_default():
    @confclass(if_scalar="test")
    class ScalarConfig:
        test: str
        other: int = 42
    
    @confclass
    class RootConfig:
        scalar: ScalarConfig = "testing"

    conf = RootConfig()
    load_config(conf, "")
    assert conf.scalar.test == "testing"
    assert conf.scalar.other == 42
    
def test_missing_defaults():
    @confclass
    class MissingDefault:
        test: str
    
    conf = MissingDefault()
    with pytest.raises(ConfclassesMissingValueError):
        load_config(conf, "")

def test_loading_error():
    @confclass
    class TestConfig:
        test: str = "test"

    conf = TestConfig()
    # Test that we get a loading error if we try to load a string
    with pytest.raises(ConfclassesLoadingError):
        load_config(conf, "hello")

    # Test that we get a loading error if we try to load a list
    with pytest.raises(ConfclassesLoadingError):
        load_config(conf, "[]")

    # Test invalid yaml raises a loading error
    with pytest.raises(ConfclassesLoadingError):
        load_config(conf, "invalid: yaml: here")