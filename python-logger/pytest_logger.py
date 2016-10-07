import os
import sys
import re
import pytest
import logging
import time
import datetime
from contextlib import contextmanager

def pytest_addoption(parser):
    group = parser.getgroup("logger", "logging")
    group.addoption('--logdirflat', default=False, action='store_true',
                     help='puts all logs in single file.')

def pytest_configure(config):
    config.pluginmanager.register(LoggerPlugin(config), '_logger')

def pytest_addhooks(pluginmanager):
    pluginmanager.add_hookspecs(LoggerHookspec)

class LoggerPlugin(object):
    def __init__(self, config):
        self.logdirlinks = config.hook.pytest_logger_logdirlink(config=config)
        self.logdirflat = config.getoption('logdirflat')

    def pytest_runtest_setup(self, item):
        def to_loggers(names_list):
            return [logging.getLogger(name) for names in names_list for name in names]

        stdoutloggers = to_loggers(item.config.hook.pytest_logger_stdoutloggers(item=item))
        fileloggers = to_loggers(item.config.hook.pytest_logger_fileloggers(item=item))

        item._logger = LoggerState(plugin=self, stdoutloggers=stdoutloggers, fileloggers=fileloggers)

        if fileloggers:
            item.fixturenames.insert(0, '_filehandlers')
        if stdoutloggers:
            item.fixturenames.insert(0, '_stdouthandlers')

    def pytest_runtest_teardown(self, item, nextitem):
        handler = item._logger.stdouthandler
        if handler:
            handler.newline_before_next_log()

class LoggerState(object):
    FORMAT = '%(asctime)s %(name)s: %(message)s'
    def __init__(self, plugin, stdoutloggers, fileloggers):
        self.plugin = plugin
        self.stdoutloggers = stdoutloggers
        self.fileloggers = fileloggers
        self.formatter = Formatter(fmt=self.FORMAT)
        self.stdouthandler = None

class LoggerHookspec(object):
    def pytest_logger_stdoutloggers(self, item):
        """ called before testcase setup, returns list of logger names """

    def pytest_logger_fileloggers(self, item):
        """ called before testcase setup, returns list of logger names """

    def pytest_logger_logdirlink(self, config):
        """ called after cmdline options parsing, returns location of link to logs dir """

@pytest.fixture(scope='session')
def _logsdir(tmpdir_factory, request):
    logsdir = tmpdir_factory.getbasetemp()
    if logsdir.basename.startswith('popen-gw'):
        logsdir = logsdir.join('..')
    logsdir = logsdir.join('logs').ensure(dir=1)

    state = request._pyfuncitem._logger
    for link in state.plugin.logdirlinks:
        _refresh_link(str(logsdir), link)

    return logsdir

@pytest.fixture
def _logdir(_logsdir, request):
    def sanitize(filename):
        filename = filename.replace('::', '-')
        filename = re.sub(r'\[(\d+)\]', r'-\1', filename)
        return filename

    return _logsdir.join(sanitize(request.node.nodeid)).ensure(dir=1)

@pytest.yield_fixture
def _stdouthandlers(request):
    def make_handler(fmt):
        handler = StdoutHandler(stream=sys.stdout)
        handler.setFormatter(fmt)
        handler.newline_before_next_log()
        return handler

    state = request._pyfuncitem._logger
    state.stdouthandler = handler = make_handler(state.formatter)
    loggers_and_handlers = [(lgr, handler) for lgr in state.stdoutloggers]

    with _handlers_added(loggers_and_handlers):
        yield

@pytest.yield_fixture
def _filehandlers(_logdir, request):
    def make_handler(logdir, name, fmt):
        logfile = str(logdir.join(name))
        handler = MyFileHandler(filename=logfile, mode='w', delay=True)
        handler.setFormatter(fmt)
        return handler

    state = request._pyfuncitem._logger
    if not state.plugin.logdirflat:
        loggers_and_handlers = [
            (lgr, make_handler(_logdir, lgr.name, state.formatter))
            for lgr in state.fileloggers
        ]
    else:
        handler = make_handler(_logdir, 'logs', state.formatter)
        loggers_and_handlers = [(lgr, handler) for lgr in state.fileloggers]

    with _handlers_added(loggers_and_handlers):
        yield

logdir = _logdir

class Formatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super(Formatter, self).__init__(*args, **kwargs)
        self._start = time.time()
    def formatTime(self, record, datefmt=None):
        ct = record.created - self._start
        dt = datetime.datetime.utcfromtimestamp(ct)
        return dt.strftime("%M:%S.%f")[:-3]  # omit useconds, leave mseconds

class StdoutHandler(logging.StreamHandler):
    def newline_before_next_log(self):
        if self.stream.name == '<stdout>':
            self.stream.write('\n')

class MyFileHandler(logging.FileHandler):
    def __init__(self, filename, **kwargs):
        logging.FileHandler.__init__(self, filename, **kwargs)

@contextmanager
def _handlers_added(loggers_and_handlers):
    for lgr, hdlr in loggers_and_handlers:
        lgr.addHandler(hdlr)
    try:
        yield
    finally:
        for lgr, hdlr in loggers_and_handlers:
            lgr.removeHandler(hdlr)

def _refresh_link(source, link_name):
    try:
        os.unlink(link_name)
    except OSError:
        pass
    try:
        os.symlink(source, link_name)
    except (OSError, AttributeError, NotImplementedError):
        pass
