from common.util import log
from resources.ipfs.commands import IPFSCommands


class IPFSPeersCheckMixin(object):

    @staticmethod
    def check_peers(peer_addresses):

        peers = IPFSCommands.peers()
        peer_hashes = [IPFSCommands.hash_from_address(p) for p in peer_addresses]
        present = {k: False for k in peer_hashes}

        for line in peers:
            for peer_hash in peer_hashes:
                if line.find(peer_hash) != -1:
                    present[peer_hash] = True

        if not all([v for v in present.itervalues()]):
            log('Not connected to all of the peers')
            log(present)