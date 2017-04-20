#!/usr/bin/env python3

# Copyright: 2015 The Debian Project
# License: MIT-License or Apache-2.0
#
# Helper to remove removed-files from .cargo-checksum
# TODO: rewrite to perl and add to dh-cargo, maybe?

from collections import OrderedDict
import json
import os
import sys

def main(pkgdir):
  os.chdir(pkgdir)
  with open(".cargo-checksum.json") as fp:
    sums = json.load(fp, object_pairs_hook=OrderedDict)
  
  oldfiles = sums["files"]
  newfiles = OrderedDict([entry for entry in oldfiles.items() if os.path.exists(entry[0])])
  sums["files"] = newfiles
  
  if len(oldfiles) > len(newfiles):
    with open(".cargo-checksum.json", "w") as fp:
      json.dump(sums, fp, separators=(',', ':'))

if __name__ == "__main__":
  main(sys.argv[1] if len(sys.argv) > 1 else ".")
