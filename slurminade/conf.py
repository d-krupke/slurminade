"""
This file saves the default configuration for slurm.
"""

import json
import os.path
from pathlib import Path


def _load_default_conf():
    default_conf_file = os.path.join(Path.home(), ".slurminade_default.json")
    try:
        if os.path.isfile(default_conf_file):
            with open(default_conf_file, "r") as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        print(
            f"slurminade could not open default configuration {default_conf_file}!\n{str(e)}"
        )
    return {}


__default_conf = _load_default_conf()


def update_default_configuration(conf=None, **kwargs):
    if conf:
        __default_conf.update(conf)
    if kwargs:
        __default_conf.update(kwargs)


def set_default_configuration(conf=None, **kwargs):
    __default_conf = {}
    update_default_configuration(conf, **kwargs)


def _get_conf(conf=None):
    conf = conf if conf else {}
    conf_ = __default_conf.copy()
    conf_.update(conf)
    return conf_
