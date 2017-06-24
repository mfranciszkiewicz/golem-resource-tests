import errno
import socket
import time
import traceback
from abc import abstractmethod, ABCMeta
from threading import Thread

import select

from message import VERSION, HEADER_SIZE, Message, MESSAGES, Resources, Address, GetResources, Result, Hello, \
    MessageWrapper, GetAddress
from common.util import log


class ProtocolError(Exception):
    pass


class ProtocolVersionError(ProtocolError):
    pass


def address_from_string(string):
    port_idx = string.rfind(':')
    address, port = string[:port_idx], int(string[port_idx + 1:])
    assert address
    return address, port


class PeerManager(object):

    def __init__(self):
        self.peers = dict()
        self.names = dict()

    def register(self, sock, name):
        address = sock.getpeername()
        self.peers[address] = (name, sock)
        self.names[name] = (address, sock)

    def unregister(self, address=None):
        sock, name = self.peers.pop(address, (None, None))
        self.names.pop(name, None)
        return sock, name

    def contains_address(self, address):
        return address in self.peers

    def contains_name(self, name):
        return name in self.names

    def get(self, address):
        return self.peers.get(address, (None, None))

    def get_by_name(self, name):
        return self.names.get(name, (None, None))


class Protocol(object):

    __metaclass__ = ABCMeta

    def __init__(self, name, address, proxy=None):
        self.messages = {c.ID: c for c in MESSAGES}
        self.peer_manager = PeerManager()

        self.name = name
        self.address = address_from_string(address)
        self.proxy = address_from_string(proxy[0]) if proxy else None
        self.proxy_peer = proxy[1] if proxy else None
        self.working = False

    @abstractmethod
    def start(self):
        pass

    def stop(self):
        self.working = False

    @abstractmethod
    def heartbeat(self):
        pass

    def on_connect(self, protocol, conn):
        self.send(conn, Hello(self.name))

    def on_disconnect(self, address):
        self.peer_manager.unregister(address)

    def on_message(self, protocol, sock, msg_wrapper):
        msg = msg_wrapper.msg
        result = self.relay(sock, msg_wrapper)

        if isinstance(msg, Hello):
            is_proxy = self.proxy_peer == msg.name
            exists = self.peer_manager.contains_name(msg.name)
            not_proxy_peer = not is_proxy or (is_proxy and not exists)

            if not self.proxy_peer or not_proxy_peer:
                self.peer_manager.register(sock, msg.name)
                result = True

        elif not self.peer_manager.contains_address(sock.getpeername()):
            raise ProtocolError("Unknown peer: {}".format(protocol.address))

        return result

    def send(self, conn, msg, dst=None):
        if not dst:
            dst = self.proxy_peer
        if not dst:
            _, dst = self.peer_manager.get(conn.getpeername())

        log('>> send {} to {}'.format(msg.__class__.__name__, dst))
        return self._sendall(conn, msg.pack(src=self.name, dst=dst or ''))

    def relay(self, conn, msg_wrapper):
        msg = msg_wrapper.msg
        src = msg_wrapper.src
        dst = msg_wrapper.dst

        if src != self.name and dst and dst != self.name:
            _, sock = self.peer_manager.get_by_name(dst)
            if not sock:
                raise ProtocolError('Unknown peer: {}'.format(dst))

            log('>> relay {} from {} to {}'.format(msg.__class__.__name__, src, dst))
            self._sendall(sock, msg.pack(src=src, dst=dst))
            return True

    def receive(self, conn):
        data = self._receive(conn, HEADER_SIZE)

        if len(data) == 0:
            raise ProtocolError('Connection terminated by other side')
        elif len(data) < HEADER_SIZE:
            raise ProtocolError('Invalid message header of length {}: |{}|'
                                .format(len(data), data))

        version, msg_id, src_len, dst_len, data_len = Message.unpack_header(data)
        src = self._receive_len(conn, src_len)
        dst = self._receive_len(conn, dst_len)
        content = self._receive_len(conn, data_len)

        wrapper = MessageWrapper(
            self.to_message(version, msg_id, content),
            src, dst
        )

        log('>> receive {} from {} to {}'.format(wrapper.msg.__class__.__name__,
                                                 wrapper.src, wrapper.dst))
        return wrapper

    def _receive_len(self, conn, length):

        read = 0
        content = bytes()

        while read < length:
            data = self._receive(conn, length - read)
            if not data:
                break
            read += len(data)
            content += data

        return content

    def to_message(self, version, msg_id, content):

        if not version == VERSION:
            raise ProtocolVersionError('Version {} not supported'
                                       .format(version))

        if msg_id in self.messages:
            cls = self.messages[msg_id]
            msg = cls.__new__(cls)
            msg.deserialize(content)
            return msg

        raise ProtocolError("Unknown message type: {}".format(msg_id))

    def _do_work(self, conn, address):
        try:
            self.on_connect(self, conn)
            while self.working:
                try:
                    message = self.receive(conn)
                    self.on_message(self, conn, message)
                except socket.error, e:
                    raise ProtocolError('Socket error: {}'.format(e))
        except ProtocolError as e:
            log('Protocol error [{}]: {}'.format(address, e))
        except Exception as e:
            log('Exception occurred [{}]: {}'.format(address, e))
            traceback.print_exc()
        finally:
            log('Closing {}'.format(address))
            self.on_disconnect(address)
            conn.close()

    @staticmethod
    def _handle_socket_error(e):
        err = e.args[0]
        if err in [errno.EAGAIN, errno.EWOULDBLOCK, errno.EINPROGRESS]:
            time.sleep(0.01)
        else:
            raise e

    def _connect(self, sock, addr):

        try:
            sock.connect(addr)
        except socket.error, e:
            self._handle_socket_error(e)

        available = False
        while not available:
            _, w, _ = select.select([], [sock], [])
            available = bool(w)

    def _sendall(self, conn, data):

        length = len(data)
        sent = 0

        while self.working:

            try:
                sent += conn.send(data[sent:])
            except socket.error, e:
                self._handle_socket_error(e)
            else:
                if sent >= length:
                    return sent

    def _receive(self, conn, amount):

        while self.working:

            try:
                data = conn.recv(amount)
            except socket.error, e:
                self._handle_socket_error(e)
            else:
                return data


class ServerProtocol(Protocol):

    __metaclass__ = ABCMeta

    def start(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)
        self.working = True

        if self.proxy:
            self._connect(sock, self.proxy)
            self._do_work(sock, self.address)
        else:
            sock.bind(self.address)
            sock.listen(1)
            log('Listening on {}'.format(self.address))
            self._work(sock)

    def on_message(self, protocol, sock, msg_wrapper):
        if not super(ServerProtocol, self).on_message(protocol, sock, msg_wrapper):

            msg = msg_wrapper.msg

            if isinstance(msg, GetResources):
                self._on_get_resources_message(protocol, sock, msg_wrapper)
            elif isinstance(msg, GetAddress):
                self._on_get_address(protocol, sock, msg_wrapper)
            elif isinstance(msg, Result):
                self._on_result_message(protocol, sock, msg_wrapper)
            else:
                raise ProtocolError('Unknown message type: {}'.format(msg))

        self.heartbeat()

    @abstractmethod
    def _on_get_resources_message(self, protocol, sock, msg_wrapper):
        pass

    @abstractmethod
    def _on_get_address(self, protocol, sock, msg_wrapper):
        pass

    @abstractmethod
    def _on_result_message(self, protocol, sock, msg_wrapper):
        pass

    def _accept(self, sock):

        while self.working:

            try:
                connection, client_address = sock.accept()
            except socket.error, e:
                self._handle_socket_error(e)
            else:
                return connection, client_address

    def _work(self, sock):

        while self.working:

            connection, client_address = self._accept(sock)

            thread = Thread(target=self._in_thread, args=(connection, client_address))
            thread.daemon = True
            thread.start()

    def _in_thread(self, connection, address):
        self._do_work(connection, address)


class ClientProtocol(Protocol):

    __metaclass__ = ABCMeta

    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)
        self.working = True

        if self.proxy:
            self._connect(sock, self.proxy)
        else:
            self._connect(sock, self.address)

        self._do_work(sock, self.address)

    def on_message(self, protocol, sock, msg_wrapper):
        if not super(ClientProtocol, self).on_message(protocol, sock, msg_wrapper):

            msg = msg_wrapper.msg

            if isinstance(msg, Resources):
                self._on_resources_message(protocol, sock, msg_wrapper)
            elif isinstance(msg, Address):
                self._on_address_message(protocol, sock, msg_wrapper)
            else:
                raise ProtocolError('Unknown message type: {}'.format(msg))

        self.heartbeat()

    @abstractmethod
    def _on_resources_message(self, protocol, sock, msg_wrapper):
        pass

    @abstractmethod
    def _on_address_message(self, protocol, sock, msg_wrapper):
        pass
