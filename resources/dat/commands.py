import os
import subprocess

import re

from resources.commands import ResourceCommands


class DatCommands(ResourceCommands):

    executable = ['dat']
    processes = dict()

    @classmethod
    def get(cls, hash_entry, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        cmd = cls.executable + [hash_entry, output_dir, '--exit']
        assert subprocess.call(cmd) == 0

    @classmethod
    def pre_publish(cls):
        for p in cls.processes.values():
            p.kill()

    @classmethod
    def publish(cls, file_path):

        process = subprocess.Popen(
            cls.executable + [os.path.dirname(file_path)],
            bufsize=1,
            stdout=subprocess.PIPE
        )
        cls.processes[file_path] = process

        address_re = re.compile("Share Link: ([a-z0-9]+)")
        while True:
            line = process.stdout.readline().strip()
            if line:
                m = address_re.match(line)
                if m:
                    print "Sharing", os.path.dirname(file_path), m.group(1)
                    return m.group(1)

    @classmethod
    def connect(cls, peer):
        pass

    @classmethod
    def start_daemon(cls, log_dir, log_file_name=None):
        pass

    @classmethod
    def stop_daemon(cls):
        pass

    @classmethod
    def address(cls):
        pass

    @classmethod
    def peers(cls):
        pass

    @classmethod
    def process(cls):
        pass

    @classmethod
    def log_level(cls, **_):
        pass
