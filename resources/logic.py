import os
import uuid
from abc import ABCMeta, abstractmethod

import shutil

from common.util import generate_file, log
from monitor.logic import Logic, timed_download
from network.message import GetAddress, Result, GetResources, Address, Resources
from network.protocol import ClientProtocol, ServerProtocol


class ResourceCreator(object):
    __metaclass__ = ABCMeta

    def __init__(self, default_file_size=10):
        self.default_file_size = default_file_size

    @abstractmethod
    def create(self, identifier, directory, file_size=None):
        pass


class OneShotResourceCreator(ResourceCreator):

    def __init__(self, default_file_size):
        super(OneShotResourceCreator, self).__init__(default_file_size)
        self.resource_dirs = dict()

    def create(self, identifier, directory, file_size=None):

        if identifier in self.resource_dirs:
            last_dir = self.resource_dirs.pop(identifier)
            if os.path.exists(last_dir):
                shutil.rmtree(last_dir)

        sub_dir = str(uuid.uuid4())
        file_size = file_size if file_size is not None else self.default_file_size
        file_path, _ = generate_file(file_size * 1024 * 1024, os.path.join(directory, sub_dir))

        self.resource_dirs[identifier] = sub_dir

        return file_path


class ResourceSession(Logic):

    __metaclass__ = ABCMeta
    commands = None

    is_daemon = True

    def __init__(self, output_dir, log_dir, file_size, peers=None, connect=False):

        super(ResourceSession, self).__init__()

        self.peers = peers or []
        self.output_dir = output_dir
        self.log_dir = log_dir
        self.manage_daemon = self.is_daemon and not self.commands.process()
        self.resource_creator = OneShotResourceCreator(file_size)
        self.direct_connections = connect

    def set_up(self, state):

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        super(ResourceSession, self).set_up(state)

        if self.manage_daemon:
            self.commands.start_daemon(self.log_dir)
            assert self.commands.process(), 'Could not start the daemon'
            self.commands.log_level()

        if self.direct_connections:
            for peer in self.peers:
                self.commands.connect(peer)

    def tear_down(self):
        if self.manage_daemon:
            self.commands.stop_daemon()

    def heartbeat(self):
        self.state.heartbeat()

    @classmethod
    @abstractmethod
    def _create_address(cls, ip_address, msg_address):
        pass


class ResourceClientSession(ResourceSession, ClientProtocol):

    __metaclass__ = ABCMeta

    def __init__(self, name, address, output_dir, log_dir, n_tasks,
                 file_size=10, proxy=None, connect=False):

        ClientProtocol.__init__(self, name, address, proxy=proxy)
        ResourceSession.__init__(self, output_dir, log_dir, file_size, connect=connect)

        self.n_tasks = n_tasks
        self.resource_dir = os.path.join(self.output_dir, 'resources_client')
        self.result_dir = os.path.join(self.output_dir, 'results_client')

    # ClientProtocol

    def on_connect(self, protocol, sock):
        super(ResourceClientSession, self).on_connect(protocol, sock)
        protocol.send(sock, GetAddress(), dst=self.proxy_peer)

    def _on_resources_message(self, protocol, sock, msg_wrapper):

        msg = msg_wrapper.msg
        for _hash in msg.hashes:
            with timed_download(self.state, protocol):
                self.commands.get(_hash, os.path.join(self.resource_dir, "d_" + _hash))
        self.commands.pre_publish()

        sub_dir = str(uuid.uuid4())
        file_path = self.resource_creator.create(msg_wrapper.src, os.path.join(self.result_dir, sub_dir))
        file_hash = self.commands.publish(file_path)
        protocol.send(sock, Result(file_hash), dst=msg_wrapper.src)

        if self.state.rounds < self.n_tasks - 1:
            self.state.new_round()
            protocol.send(sock, GetResources(), dst=msg_wrapper.src)
        else:
            self.stop()

    def _on_address_message(self, protocol, sock, msg_wrapper):
        if self.direct_connections:

            msg = msg_wrapper.msg
            address = self._create_address(self.address[0], msg.address)

            try:
                self.commands.connect(address)
            except Exception as exc:
                log('Error connecting to {}: {}'.format(address, exc))

        protocol.send(sock, GetResources(), dst=msg_wrapper.src)

    # Logic

    def next(self):
        if not self.working:
            raise StopIteration()
        return True

    def set_up(self, state):
        ResourceSession.set_up(self, state)
        self.start()

    def stop(self):
        super(ResourceClientSession, self).stop()
        self.state.done = True


class ResourceServerSession(ResourceSession, ServerProtocol):

    __metaclass__ = ABCMeta

    def __init__(self, name, address, output_dir, log_dir,
                 file_size=10, proxy=None, connect=False):

        ServerProtocol.__init__(self, name, address, proxy=proxy)
        ResourceSession.__init__(self, output_dir, log_dir, file_size, connect=connect)

        self.file_size = file_size
        self.resource_dir = os.path.join(self.output_dir, 'resources_server')
        self.result_dir = os.path.join(self.output_dir, 'results_server')

    # ServerProtocol

    def _on_get_address(self, protocol, sock, msg_wrapper):
        address = self.commands.address()
        protocol.send(sock, Address(address), dst=msg_wrapper.src)

    def _on_get_resources_message(self, protocol, sock, msg_wrapper):
        resources = []
        self.commands.pre_publish()

        for i in xrange(3):
            sub_dir = str(uuid.uuid4())
            file_path = self.resource_creator.create(msg_wrapper.src, os.path.join(self.resource_dir, sub_dir))
            file_hash = self.commands.publish(file_path)
            resources.append(file_hash)

        protocol.send(sock, Resources(resources), dst=msg_wrapper.src)

    def _on_result_message(self, protocol, sock, msg_wrapper):
        msg = msg_wrapper.msg
        with timed_download(self.state, protocol):
            self.commands.get(msg.result_hash, os.path.join(self.result_dir, "d_" + msg.result_hash))
        self.state.new_round()

    # Logic

    def next(self):
        if not self.working:
            raise StopIteration()
        return True

    def set_up(self, state):
        super(ResourceServerSession, self).set_up(state)
        state.timeout = -1
        self.start()

    def tear_down(self):
        super(ResourceServerSession, self).tear_down()
        self.stop()
