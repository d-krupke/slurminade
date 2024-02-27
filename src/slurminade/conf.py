"""
This file saves the default configuration for slurm.
"""

import json
import os.path
import typing
from pathlib import Path

CONFIG_NAME = ".slurminade_default.json"

__default_conf: typing.Dict = {}


def _load_conf(path: Path):
    try:
        if path.is_file():
            with path.open() as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        print(f"slurminade could not open default configuration {path}!\n{e!s}")
    return {}


def update_default_configuration(conf=None, **kwargs):
    """
    Adds or updates the default configuration.
    :param conf: A dictionary with the configuration.
    :param kwargs: Configuration parameters. (alternative to giving a dictionary)
    """
    if conf:
        __default_conf.update(conf)
    if kwargs:
        __default_conf.update(kwargs)


def _load_default_conf():
    path = Path.home() / CONFIG_NAME
    update_default_configuration(_load_conf(path))
    if "XDG_CONFIG_HOME" in os.environ:
        path = Path(os.environ["XDG_CONFIG_HOME"]) / "slurminade" / CONFIG_NAME
        update_default_configuration(_load_conf(path))
    update_default_configuration(_load_conf(Path(CONFIG_NAME)))


_load_default_conf()


def set_default_configuration(conf=None, **kwargs):
    """
    Replaces the default configuration.
    This will overwrite the default configuration with the given one.
    :param conf: A dictionary with the configuration.
    :param kwargs: Configuration parameters. (alternative to giving a dictionary)
    """
    __default_conf = {}
    update_default_configuration(conf, **kwargs)


def _get_conf(conf=None):
    conf = conf if conf else {}
    conf_ = __default_conf.copy()
    conf_.update(conf)
    return conf_
