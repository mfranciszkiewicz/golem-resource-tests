from resources.ipfs.commands import IPFSCommands
from resources.logic import ResourceClientSession, ResourceServerSession


class IPFSAddressCreatorMixin(object):
    @classmethod
    def _create_address(cls, ip_address, msg_address):
        return '/ip{}/{}/tcp/4001/ipfs/{}'.format(
            '4' if ip_address.find(':') == -1 else '6',
            ip_address,
            msg_address
        )


class IPFSClientSession(IPFSAddressCreatorMixin, ResourceClientSession):
    commands = IPFSCommands


class IPFSServerSession(IPFSAddressCreatorMixin, ResourceServerSession):
    commands = IPFSCommands
