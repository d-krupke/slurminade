"""Tests for SlurmOptions class."""

import pytest

from slurminade.options import SlurmOptions


def test_slurmoptions_basic():
    """Test basic SlurmOptions creation and access."""
    opts = SlurmOptions(partition="test", memory="4GB")
    assert opts["partition"] == "test"
    assert opts["memory"] == "4GB"


def test_slurmoptions_contains():
    """Test 'in' operator."""
    opts = SlurmOptions(partition="test")
    assert "partition" in opts
    assert "memory" not in opts


def test_slurmoptions_get():
    """Test get method with default."""
    opts = SlurmOptions(partition="test")
    assert opts.get("partition") == "test"
    assert opts.get("memory", "default") == "default"


def test_slurmoptions_setitem():
    """Test setting items."""
    opts = SlurmOptions(partition="test")
    opts["memory"] = "8GB"
    assert opts["memory"] == "8GB"


def test_slurmoptions_hash():
    """Test that SlurmOptions can be hashed."""
    opts1 = SlurmOptions(partition="test", memory="4GB")
    opts2 = SlurmOptions(partition="test", memory="4GB")
    opts3 = SlurmOptions(partition="test", memory="8GB")

    # Same options should have same hash
    assert hash(opts1) == hash(opts2)

    # Different options should have different hash (usually)
    assert hash(opts1) != hash(opts3)


def test_slurmoptions_equality():
    """Test equality comparison."""
    opts1 = SlurmOptions(partition="test", memory="4GB")
    opts2 = SlurmOptions(partition="test", memory="4GB")
    opts3 = SlurmOptions(partition="test", memory="8GB")

    assert opts1 == opts2
    assert opts1 != opts3
    assert opts1 != "not an option"


def test_slurmoptions_as_dict():
    """Test conversion to dict."""
    opts = SlurmOptions(partition="test", memory="4GB")
    d = opts.as_dict()
    assert isinstance(d, dict)
    assert d["partition"] == "test"
    assert d["memory"] == "4GB"


def test_slurmoptions_add_dependencies_new():
    """Test adding dependencies when none exist."""
    opts = SlurmOptions(partition="test")
    opts.add_dependencies([123, 456])
    assert "dependency" in opts
    assert opts["dependency"] == "afterany:123:456"


def test_slurmoptions_add_dependencies_extend_string():
    """Test extending existing string dependencies."""
    opts = SlurmOptions(partition="test")
    opts["dependency"] = "afterany:111:222"
    opts.add_dependencies([333, 444])
    assert "afterany:333:444" in opts["dependency"]


def test_slurmoptions_add_dependencies_with_method():
    """Test adding dependencies with custom method."""
    opts = SlurmOptions(partition="test")
    opts.add_dependencies([123], method="afterok")
    assert opts["dependency"] == "afterok:123"


def test_slurmoptions_items():
    """Test items() method."""
    opts = SlurmOptions(partition="test", memory="4GB")
    items = list(opts.items())
    assert len(items) == 2
    assert ("partition", "test") in items
    assert ("memory", "4GB") in items


def test_slurmoptions_keys():
    """Test keys() method."""
    opts = SlurmOptions(partition="test", memory="4GB")
    keys = list(opts.keys())
    assert "partition" in keys
    assert "memory" in keys


def test_slurmoptions_values():
    """Test values() method."""
    opts = SlurmOptions(partition="test", memory="4GB")
    values = list(opts.values())
    assert "test" in values
    assert "4GB" in values


def test_slurmoptions_update():
    """Test update() method."""
    opts = SlurmOptions(partition="test")
    opts.update({"memory": "8GB", "cpus": 4})
    assert opts["memory"] == "8GB"
    assert opts["cpus"] == 4


def test_slurmoptions_copy():
    """Test copy() method."""
    opts1 = SlurmOptions(partition="test", memory="4GB")
    opts2 = opts1.copy()

    assert opts1 == opts2
    assert opts1 is not opts2

    # Modifying copy shouldn't affect original
    opts2["memory"] = "8GB"
    assert opts1["memory"] == "4GB"


def test_slurmoptions_repr():
    """Test string representation."""
    opts = SlurmOptions(partition="test")
    repr_str = repr(opts)
    assert "SlurmOptions" in repr_str
    assert "partition" in repr_str


def test_slurmoptions_unhashable_value():
    """Test that unhashable values raise TypeError on hash."""
    opts = SlurmOptions(partition="test")
    opts["bad_list"] = [1, 2, 3]  # Lists are not hashable

    with pytest.raises(TypeError, match="Cannot hash SlurmOptions"):
        hash(opts)


def test_slurmoptions_can_be_used_as_dict_key():
    """Test that SlurmOptions can be used as dictionary keys."""
    opts1 = SlurmOptions(partition="test", memory="4GB")
    opts2 = SlurmOptions(partition="test", memory="8GB")

    cache = {opts1: "result1", opts2: "result2"}

    assert cache[opts1] == "result1"
    assert cache[opts2] == "result2"


def test_slurmoptions_nested_dict():
    """Test handling of nested dictionaries."""
    opts = SlurmOptions(partition="test", nested={"key": "value"})

    # The nested dict should be converted to SlurmOptions in _items()
    items_dict = opts.as_dict()
    assert "nested" in items_dict
