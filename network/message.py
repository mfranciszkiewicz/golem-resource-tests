import struct
from collections import namedtuple

import jsonpickle

SHORT_LEN = 65535

VERSION = '1'
HEADER_STRUCT_FMT = '!chhhh'
HEADER_STRUCT = struct.Struct(HEADER_STRUCT_FMT)
HEADER_SIZE = HEADER_STRUCT.size


MessageWrapper = namedtuple('MessageWrapper', ['msg', 'src', 'dst'])


class Message(object):
    ID = 0

    def pack(self, src, dst=''):
        src = str(src) or ''
        dst = str(dst) or ''

        serialized = str(self.serialize())
        content_len = len(str(serialized))
        src_len = len(src)
        dst_len = len(dst)

        header = struct.Struct('{}{}s{}s{}s'.format(HEADER_STRUCT_FMT,
                                                    src_len, dst_len,
                                                    content_len))
        return header.pack(VERSION, self.ID,
                           src_len, dst_len, content_len,
                           src, dst, serialized)

    @staticmethod
    def unpack_header(data):
        version, msg_id, src_len, dst_len, content_len = \
            struct.unpack(HEADER_STRUCT_FMT, data[:HEADER_SIZE])
        return version, msg_id, src_len, dst_len, content_len

    def serialize(self):
        return ''

    def deserialize(self, content):
        pass


class Hello(Message):
    ID = 1

    def __init__(self, name):
        super(Hello, self).__init__()
        self.name = name

    def deserialize(self, name):
        self.name = str(name).strip()

    def serialize(self):
        return self.name


class GetAddress(Message):
    ID = 10


class Address(Message):
    ID = 11

    def __init__(self, address):
        super(Address, self).__init__()
        self.address = address

    def deserialize(self, content):
        self.address = str(content).strip()

    def serialize(self):
        return self.address


class GetResources(Message):
    ID = 20


class Resources(Message):
    ID = 21

    def __init__(self, hashes):
        super(Resources, self).__init__()
        self.hashes = hashes

    def deserialize(self, content):
        if content:
            self.hashes = jsonpickle.loads(content)

    def serialize(self):
        return jsonpickle.dumps(self.hashes)


class Result(Message):
    ID = 30

    def __init__(self, result_hash):
        super(Result, self).__init__()
        self.result_hash = result_hash

    def deserialize(self, content):
        self.result_hash = str(content).strip()

    def serialize(self):
        return self.result_hash


def _collect_message_classes():
    import inspect
    import sys

    result = []

    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj) and issubclass(obj, Message) and obj is not Message:
            result.append(obj)

    return result


MESSAGES = _collect_message_classes()
