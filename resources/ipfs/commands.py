import os
import subprocess
import time

import psutil

from resources.commands import ResourceCommands


class IPFSCommands(ResourceCommands):

    @classmethod
    def peers(cls):
        return subprocess.check_output(['ipfs', 'swarm', 'peers']).split('\n')

    @classmethod
    def address(cls):
        cmd = ['ipfs', 'id', '-f="<id>"']
        address = subprocess.check_output(cmd).replace('"', '')
        assert address
        return address

    @classmethod
    def start_daemon(cls, log_dir, log_file_name=None):
        if not log_file_name:
            log_file_name = 'daemon_{}.log'.format(time.time())
        log_file_path = os.path.join(log_dir, log_file_name)

        cmd = ['ipfs', 'daemon']
        assert subprocess.Popen(cmd,
                                stdout=open(log_file_path, 'wb'),
                                stderr=subprocess.STDOUT).pid
        time.sleep(5)

    @classmethod
    def stop_daemon(cls):
        p = cls.process()
        if p and p.pid:
            p.kill()

    @classmethod
    def pre_publish(cls):
        pass

    @classmethod
    def publish(cls, file_path):
        cmd = ['ipfs', 'add', file_path]
        output = subprocess.check_output(cmd).strip().replace('"', '')
        return output.split(' ')[-2]

    @classmethod
    def connect(cls, peer):
        cmd = ['ipfs', 'swarm', 'connect', peer]
        assert subprocess.call(cmd) == 0

    @classmethod
    def get(cls, hash_entry, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        cmd = ['ipfs', 'get', '/ipfs/{}'.format(hash_entry), '-o', output_dir]
        assert subprocess.call(cmd) == 0

    @classmethod
    def log_level(cls, _all='debug', _dht='warning', **kwargs):
        assert subprocess.call(['ipfs', 'log', 'level', 'all', _all]) == 0
        assert subprocess.call(['ipfs', 'log', 'level', 'dht', _dht]) == 0

    @classmethod
    def process(cls):
        process_names = ['ipfs.exe', 'ipfs']
        for p in psutil.process_iter():
            if p.name() in process_names:
                return p

    @classmethod
    def hash_from_address(cls, source):
        return source.split('/')[-1]
