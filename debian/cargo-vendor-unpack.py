#!/usr/bin/env python

# Copyright: 2015 The Debian Project
# License: MIT-License or Apache-2.0
#
# Helper to unpack a local crate registry to original sources
# TODO: rewrite to perl, maybe?

import os
import tarfile

def main():
  curdir = os.getcwd()
  depsdir = os.path.join(curdir, "deps")
  vendordir = os.path.join(curdir, "vendor")
  cachedir = os.path.join(vendordir, "cache")
  if not os.path.exists(depsdir):
    os.makedirs(depsdir)

  for _, names, _ in os.walk(top=cachedir):
    for cratename in names:
      for _, vers, _ in os.walk(top=os.path.join(cachedir, cratename)):
        for cratever in vers:
          crate = os.path.join(cachedir, cratename, cratever, "download")
          tar = tarfile.open(crate)
          tar.extractall(path=depsdir)
          print("Unpacking crate deps %s" % crate)
          tar.close()


if __name__ == "__main__":
  main()
