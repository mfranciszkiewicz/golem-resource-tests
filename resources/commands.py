from abc import abstractmethod, ABCMeta


class ResourceCommands(object):

    __metaclass__ = ABCMeta

    @classmethod
    @abstractmethod
    def peers(cls):
        pass

    @classmethod
    @abstractmethod
    def address(cls):
        pass

    @classmethod
    @abstractmethod
    def start_daemon(cls, log_dir, log_file_name=None):
        pass

    @classmethod
    @abstractmethod
    def stop_daemon(cls):
        pass

    @classmethod
    @abstractmethod
    def pre_publish(cls):
        pass

    @classmethod
    @abstractmethod
    def publish(cls, file_path):
        pass

    @classmethod
    @abstractmethod
    def connect(cls, peer):
        pass

    @classmethod
    @abstractmethod
    def get(cls, hash_entry, output_dir):
        pass

    @classmethod
    @abstractmethod
    def log_level(cls, **_):
        pass

    @classmethod
    @abstractmethod
    def process(cls):
        pass
