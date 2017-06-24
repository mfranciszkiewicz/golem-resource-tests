from resources.dat.commands import DatCommands
from resources.logic import ResourceServerSession, ResourceClientSession


class DatClientSession(ResourceClientSession):
    commands = DatCommands
    is_daemon = False

    @classmethod
    def _create_address(cls, ip_address, msg_address):
        return msg_address


class DatServerSession(ResourceServerSession):
    commands = DatCommands
    is_daemon = False

    @classmethod
    def _create_address(cls, ip_address, msg_address):
        return msg_address
