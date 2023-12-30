"""
This file saves the default configuration for slurm.
"""

import json
import os.path
import typing
from pathlib import Path

CONFIG_NAME = ".slurminade_default.json"

__default_conf: typing.Dict = {}


def _load_conf(path):
    try:
        if os.path.isfile(path):
            with open(path) as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        print(f"slurminade could not open default configuration {path}!\n{e!s}")
    return {}


def update_default_configuration(conf=None, **kwargs):
    if conf:
        __default_conf.update(conf)
    if kwargs:
        __default_conf.update(kwargs)


def _load_default_conf():
    path = os.path.join(Path.home(), CONFIG_NAME)
    update_default_configuration(_load_conf(path))
    if "XDG_CONFIG_HOME" in os.environ:
        path = os.path.join(os.environ["XDG_CONFIG_HOME"], "slurminade", CONFIG_NAME)
        update_default_configuration(_load_conf(path))
    update_default_configuration(_load_conf(CONFIG_NAME))


_load_default_conf()


def set_default_configuration(conf=None, **kwargs):
    __default_conf = {}
    update_default_configuration(conf, **kwargs)


def _get_conf(conf=None):
    conf = conf if conf else {}
    conf_ = __default_conf.copy()
    conf_.update(conf)
    return conf_
