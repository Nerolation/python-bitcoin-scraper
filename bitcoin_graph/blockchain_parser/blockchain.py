# Copyright (C) 2015-2016 The bitcoin-blockchain-parser developers
#
# This file is part of bitcoin-blockchain-parser.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of bitcoin-blockchain-parser, including this file, may be copied,
# modified, propagated, or distributed except according to the terms contained
# in the LICENSE file.
#
# This file was altered in many ways in comparison to the file which it was
# forked from. Primarily most of the logic moved into the Parser file.
# The ordered block method was completely abondoned to use the programm
# without leveldb installed.

import os
import mmap
import struct
import stat

from .block import Block


# Constant separating blocks in the .blk files
BITCOIN_CONSTANT = b"\xf9\xbe\xb4\xd9"


def get_files(path):
    """
    Given the path to the .bitcoin directory, returns the sorted list of .blk
    files contained in that directory
    """
    if not stat.S_ISDIR(os.stat(path)[stat.ST_MODE]):
        return [path]
    files = os.listdir(path)
    files = [f for f in files if f.startswith("blk") and f.endswith(".dat")]
    files = map(lambda x: os.path.join(path, x), files)
    return sorted(files)


def get_blocks(blockfile):
    """
    Given the name of a .blk file, for every block contained in the file,
    yields its raw hexadecimal value
    """
    with open(blockfile, "rb") as f:
        if os.name == 'nt':
            size = os.path.getsize(f.name)
            raw_data = mmap.mmap(f.fileno(), size, access=mmap.ACCESS_READ)
        else:
            # Unix-only call, will not work on Windows, see python doc.
            raw_data = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)
        length = len(raw_data)
        offset = 0
        while offset < (length - 4):
            if raw_data[offset:offset+4] == BITCOIN_CONSTANT:
                offset += 4
                size = struct.unpack("<I", raw_data[offset:offset+4])[0]
                offset += 4 + size
                yield raw_data[offset-size:offset]
            else:
                offset += 1
        raw_data.close()
        

class Blockchain(object):
    """Represents the blockchain contained in the series of .blk files
    maintained by bitcoind.
    """

    def __init__(self, path):
        self.path = path
        self.blockIndexes = None
        self.indexPath = None

    def get_blk_files(self, sF, eF):
        blk_files = get_files(self.path)
        blk_files = blk_files[blk_files.index(self.path + "/" + sF):]
        if eF:
            blk_files = blk_files[:blk_files.index(self.path + "/" + eF)+1]
        return blk_files
        
    def get_unordered_blocks(self, blk_file):
        """Yields the blocks contained in a .blk file as is,
        without ordering them according to height.
        """
        for raw_block in get_blocks(blk_file):
            yield Block(raw_block)
