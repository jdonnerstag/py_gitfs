#!/usr/bin/env python

import os

__version__ = ''
with open("src/fs_gitfs/_version.py") as f:
    exec(f.read())

from setuptools import setup

setup(
    version = __version__,
    entry_points = {"fs.opener": ["git = fs_gitfs.opener:GITFSOpener"]},
)
