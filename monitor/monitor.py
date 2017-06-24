from __future__ import absolute_import

import time
import traceback
from threading import Thread

import pandas as pd

from common.util import log
from monitor.logic import Logic


class Monitor(object):

    class State(object):

        def __init__(self, timeout):
            self.last_heartbeat = time.time()

            self.downloads = dict()
            self.rounds = 0
            self.timeout = timeout

            self.done = False
            self.exception = None
            self.backtrace = None

        def heartbeat(self):
            self.last_heartbeat = time.time()

        def timed_out(self, timeout):
            return timeout > 0 and self.last_heartbeat + timeout <= time.time()

        def new_round(self):
            self.rounds += 1

        def __repr__(self):
            aggregated = []
            partial = {}

            for k, v in self.downloads.iteritems():
                aggregated += v
                partial[k] = pd.DataFrame(v)

            res = "Total:\n{}\n".format(self.__stats(pd.DataFrame(aggregated)))
            for k, v in partial.iteritems():
                res += "\n{}:\n{}\n".format(k, self.__stats(v))
            return res

        @staticmethod
        def __stats(data_frame):
            if data_frame.empty:
                return dict()
            return data_frame.describe(
                [.01, .05, .1, .25, .5, .75, .9, .95, .99]
            )

    def __init__(self, logic, timeout=120):

        assert_msg = 'Invalid logic class: {}'.format(logic.__class__.__name__)
        assert isinstance(logic, Logic), assert_msg

        self.logic = logic
        self.timeout = timeout

    def start(self):
        state = self.State(self.timeout)

        def job():
            try:
                for _ in self.logic:
                    pass
            except Exception as e:
                state.backtrace = traceback.format_exc()
                state.exception = e
            else:
                state.done = True

        self.logic.set_up(state)

        thread = Thread(target=job)
        thread.daemon = True
        thread.start()

        try:

            while not state.done and thread.is_alive:
                if state.timed_out(state.timeout):
                    raise Exception('Test timed out after {} s'
                                    .format(state.timeout))
                time.sleep(0.5)

            if not state.done:
                raise Exception('Test incomplete')

        except KeyboardInterrupt:
            pass

        except Exception as exc:
            log("Test session exception: {}".format(exc))

        finally:
            self.logic.tear_down()

            if state.exception:
                log('Test exception: {}'.format(state.exception))
                log(state.backtrace)

            log('Test state result:\n{}'.format(state))
