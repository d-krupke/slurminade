_default_conf = {}


def update_default_configuration(conf=None, **kwargs):
    if conf:
        _default_conf.update(conf)
    if kwargs:
        _default_conf.update(kwargs)


def set_default_configuration(conf=None, **kwargs):
    __default_conf = {}
    update_default_configuration(conf, **kwargs)

def _get_conf(conf=None):
    conf = conf if conf else {}
    conf_ = _default_conf.copy()
    conf_.update(conf)
    return conf_