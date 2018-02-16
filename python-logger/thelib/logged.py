import time
import pprint
import logging
from functools import wraps

logger = logging.getLogger('thelib')
logger.addHandler(logging.NullHandler())

def logged(fun):
    desc = next((desc for desc in (staticmethod, classmethod) if isinstance(fun, desc)), None)
    if desc:
        fun = fun.__func__

    @wraps(fun)
    def wrap(*args, **kwargs):
        cls, nonselfargs = _declassify(fun, args)

        if _logging.currently:
            return fun(*args, **kwargs)

        with _logging:
            for line in _func_call_to_lines(fun, cls, nonselfargs, kwargs):
                logger.info(line)
            with _Timed() as t:
                ret = fun(*args, **kwargs)
            for line in _func_ret_to_lines(t.duration, ret):
                logger.info(line)
            return ret
    wrap.original = fun

    if desc:
        wrap = desc(wrap)
    return wrap

def _declassify(fun, args):
    if len(args):
        met = getattr(args[0], fun.__name__, None)
        if met:
            wrap = getattr(met, '__func__', None)
            if wrap.original is fun:
                maybe_cls = args[0]
                cls = getattr(maybe_cls, '__class__', maybe_cls)
                return cls, args[1:]
    return None, args

def _func_call_to_lines(fun, cls, args, kwargs):
    return [_to_path(fun, cls)] + _indent(_flatten_lines(
        ['%s: %s' % (i, pprint.pformat(a)) for i, a in enumerate(args)] +
        ['%s: %s' % (k, pprint.pformat(v)) for k, v in kwargs.items()]
    ))

def _func_ret_to_lines(duration, ret):
    return _indent(_flatten_lines(['-> (%.2fs) %s' % (duration, pprint.pformat(ret))]))

def _flatten_lines(lines):
    out = []
    for line in lines:
        rawlines = line.splitlines()
        out.append(rawlines[0])
        out.extend(_indent(rawlines[1:]))
    return out

def _to_path(fun, cls):
    physical_path = fun.__module__.replace('.', '/') + '.py:%s' % fun.__code__.co_firstlineno
    logical_path = (cls.__name__ + '.' if cls else '') + fun.func_name
    return '%s %s' % (physical_path, logical_path)

def _indent(lines):
    indent = ' ' * 4
    return [indent + line for line in lines]

class _Timed:
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *_):
        end = time.time()
        self.duration = end - self.start

class _Logging:
    def __init__(self):
        self.currently = False

    def __enter__(self):
        self.currently = True

    def __exit__(self, *_):
        self.currently = False

_logging = _Logging()
