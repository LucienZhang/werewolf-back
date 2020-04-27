import json

from functools import singledispatch
from werewolf.utils.enums import GameEnum


@singledispatch
def convert(o):
    raise TypeError('not special type')


@convert.register(GameEnum)
def _(o):
    return {'__GameEnum__': o.value}


class ExtendedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return convert(obj)
        except TypeError:
            return super().default(obj)


def json_hook(d):
    if '__GameEnum__' in d:
        return GameEnum(d['__GameEnum__'])
    else:
        return d
