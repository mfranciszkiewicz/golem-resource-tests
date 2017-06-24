import hashlib
import os
import random
import sys
import time

import multihash

SHA1_BLOCK_SIZE = 65536
DEV_NULL = open(os.devnull, 'w')


def generate_file(size_bytes, output_dir):

    data = bytearray(random.getrandbits(8) for _ in xrange(size_bytes))
    sha = hashlib.sha256()

    start = 0
    while start < size_bytes:
        buf = data[start:start+SHA1_BLOCK_SIZE]
        start += SHA1_BLOCK_SIZE
        sha.update(buf)

    digest = sha.hexdigest()
    encoded = multihash.encode(digest, multihash.SHA2_256)
    file_name = ''.join('{:02x}'.format(x) for x in encoded)
    file_path = os.path.join(output_dir, file_name)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(file_path, 'wb') as f:
        f.write(data)
    return file_path, file_name


def log(message):
    sys.stdout.write('[{}] {}\n'.format(time.time(), message))
