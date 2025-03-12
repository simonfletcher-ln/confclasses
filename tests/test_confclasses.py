from confclasses import confclass, load_config, ConfclassesLoadingError, save_config
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
    
    a = TestConfig()
    return TestConfig


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

def test_hashing(test_config):
    """ Make sure hashed fields do not polute """
    conf1 = test_config()
    conf2 = test_config()
    load_config(conf1, "")
    load_config(conf2, "")
    assert len(conf1.hashed_field1) == 2
    conf1.hashed_field1.append("new")
    assert len(conf2.hashed_field1) == 2

def test_none_defaults(test_config):
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

def test_save(test_config):
    conf = test_config()
    load_config(conf, "")
    assert save_config(conf) == """nested:
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

def test_save_comments(test_config):
    @confclass
    class SmallExample:
        foo: str = "test"
    
    conf = SmallExample()
    load_config(conf, "")
    assert save_config(conf, True) == """
# === foo ===
# type: Text
foo: test
"""