"""Tests for configuration management."""

import pytest
from slurminade.conf import (
    set_default_configuration,
    update_default_configuration,
    _get_conf,
)


def test_set_default_configuration():
    """Test that set_default_configuration properly clears and sets config."""
    # First, set some initial configuration
    update_default_configuration(partition="test1", memory="4GB")
    conf = _get_conf()
    assert "partition" in conf
    assert conf["partition"] == "test1"
    assert conf["memory"] == "4GB"

    # Now use set_default_configuration to replace it
    set_default_configuration(partition="test2", cpus=4)
    conf = _get_conf()

    # Old values should be gone
    assert "memory" not in conf

    # New values should be present
    assert conf["partition"] == "test2"
    assert conf["cpus"] == 4


def test_update_default_configuration():
    """Test that update_default_configuration adds to existing config."""
    # Clear first
    set_default_configuration()

    # Add some config
    update_default_configuration(partition="test")
    conf = _get_conf()
    assert conf["partition"] == "test"

    # Update with more config
    update_default_configuration(memory="8GB")
    conf = _get_conf()

    # Both should be present
    assert conf["partition"] == "test"
    assert conf["memory"] == "8GB"


def test_set_default_configuration_with_dict():
    """Test set_default_configuration with a dictionary argument."""
    config_dict = {"partition": "alg", "exclusive": True, "time": "01:00:00"}
    set_default_configuration(conf=config_dict)

    conf = _get_conf()
    assert conf["partition"] == "alg"
    assert conf["exclusive"] is True
    assert conf["time"] == "01:00:00"


def test_update_default_configuration_with_dict():
    """Test update_default_configuration with a dictionary argument."""
    set_default_configuration(partition="test")

    config_dict = {"memory": "16GB", "cpus": 8}
    update_default_configuration(conf=config_dict)

    conf = _get_conf()
    assert conf["partition"] == "test"  # Should still be there
    assert conf["memory"] == "16GB"
    assert conf["cpus"] == 8


def test_get_conf_with_override():
    """Test that _get_conf properly merges with override dict."""
    set_default_configuration(partition="default", memory="4GB")

    # Override should take precedence
    conf = _get_conf({"partition": "override"})
    assert conf["partition"] == "override"
    assert conf["memory"] == "4GB"  # Should still have default


def test_get_conf_empty():
    """Test _get_conf with no configuration."""
    set_default_configuration()
    conf = _get_conf()
    assert isinstance(conf, dict)
    assert len(conf) == 0
