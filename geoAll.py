#! /usr/bin/python3
# -*- coding-utf-8 -*-

"""
This script transform a md file into a plain html in the context of a
documentation for Kit&Pack.
"""

import argparse
import os
import re
import yaml

from lib.geoBuild import geoBuild

#from os.path import join, getsize

print("------------------------- geoAll --")
print("-- by antoine.delhomme@espci.org --")
print("-----------------------------------")

# Parse arguments
parser = argparse.ArgumentParser(
    description='Build the web version of Kit&Pack documentation.')

parser.add_argument('-i', dest='dir_in', required=True,
    help='Input directory')
parser.add_argument('-o', dest='dir_out', required=True,
    help='Output directory')

args = parser.parse_args()

dir_in = args.dir_in
dir_out = args.dir_out

doc_index = {}

for root, dirs, files in os.walk(dir_in):
    if '.git' in dirs:
        # Do not explore the .git dir
        dirs.remove('.git')

    if dir_in == root:
        # Skip the root directory
        continue

    # Filter files to keep *.md files
    filesToProcess = [ root + "/" + f for f in files if re.match('.+\.md', f) ]

    # Process each of them
    for f in filesToProcess:

        print('%s' % f)

        with geoBuild(f, dir_out) as g:
            # Parse the file
            g.parse()

            # Save metadata in the index
            project_id = g.header['long_project_id']
            name = g.header['name']
            version = g.header['version']

            if project_id not in doc_index:
                doc_index[project_id] = {}

            doc_index[project_id]["name"] = name
            versions = doc_index[project_id].get("versions_all", [])
            doc_index[project_id]["versions_all"] = versions + [version]

for project_id in doc_index.keys():
    doc_index[project_id]["version_last"] = max(doc_index[project_id]["versions_all"])

doc_index_file = "%s/docs.yaml" % dir_out

with open(doc_index_file, 'w') as f:
    yaml.dump(doc_index, f)
