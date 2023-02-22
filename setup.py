#!/usr/bin/env python

from setuptools import setup, find_packages

__version__ = ''
with open("fs_gitfs/_version.py") as f:
    exec(f.read())

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Topic :: System :: Filesystems",
]

with open("README.md", "rt") as f:
    DESCRIPTION = f.read()

REQUIREMENTS = ["fs~=2.4", "six~=1.10"]

setup(
    name="fs-gitfs",
    author="Juergen Donnerstag",
    author_email="juergen.donnerstag@gmail.com",
    classifiers=CLASSIFIERS,
    description="GIT filesystem for PyFilesystem2",
    install_requires=REQUIREMENTS,
    license="MIT",
    long_description=DESCRIPTION,
    packages=find_packages(),
    keywords=["pyfilesystem", "git"],
    platforms=["any"],
    test_suite="nose.collector",
    url="https://github.com/jdonnerstag/py_gitfs",
    version=__version__,
    entry_points={"fs.opener": ["git = fs_gitfs.opener:GITFSOpener"]},
)
