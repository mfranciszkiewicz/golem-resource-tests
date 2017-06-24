import time
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager


class Logic(object):

    __metaclass__ = ABCMeta

    def __init__(self):
        self.state = None

    def __iter__(self):
        return self

    @abstractmethod
    def next(self):
        pass

    def set_up(self, state):
        self.state = state

    @abstractmethod
    def tear_down(self):
        pass


@contextmanager
def timed_download(state, protocol):

    started = time.time()
    yield
    elapsed = time.time() - started

    if protocol.address in state.downloads:
        state.downloads[protocol.address].append(elapsed)
    else:
        state.downloads[protocol.address] = [elapsed]
