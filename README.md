# GITFS

Sometimes our applications require files (e.g. configs) which
are stored in a git repository. Different environments may use different
git repos, branches or release-tags, and sometimes we need the configs from
within a specific branch, but committed before a specific date/time.

[PyFilesystem](https://www.pyfilesystem.org/) is a Python module that provides
a common interface to any filesystem.

[GITFS](http://fs-gitfs.readthedocs.io/en/latest/) extends
[PyFilesystem](https://www.pyfilesystem.org/) and provides *read-only* access
to files stored in a git repository.

GITFS 'exports' the files related to a branch, release-tag or revision into a
temporary local directory or filesystem (e.g. in-memory filesystem), where they
can easily be accessed by our application. By default, this directory is
auto-deleted upon closing the GITFS.

With our use cases, we do not need a full clone of the git repository. We just
need the files related to a branch, release-tag or revision. Which is why we
try to export only the files needed from the remote repository.

## Installing

Install GITFS with pip as follows:

```
pip install fs-gitfs
```

## Opening a GITFS

Open a GITFS by explicitly using the constructor:

```python
from fs_gitfs import GITFS

gitfs = GITFS('https://github.com/myname/myrepo.git')
gitfs = GITFS('/home/me/my_existing_repo')
gitfs = GITFS('/home/me/my_existing_repo', branch="system_test")
gitfs = GITFS('/home/me/my_existing_repo', release="v1.0.0")
gitfs = GITFS('/home/me/my_existing_repo', branch="master", before=datetime(2021, 2, 3))
gitfs = GITFS('/home/me/my_existing_repo', local_dir="/home/configs", auto_delete=False)

```

Or with a FS URL:

```python
  from fs import open_fs

  gitfs = open_fs('git://github.com/myname/myrepo.git')
  gitfs = open_fs('git:/home/me/my_existing_repo?branch=system_test')
  gitfs = open_fs('git:/home/me/my_existing_repo?release=v1.0.0')
  gitfs = open_fs('git:/home/me/my_existing_repo?branch=master&before=2021-02-03')
```

Once created, the GITFS object should not be changed, e.g. change the branch.
Rather create a new GITFS.


## Dev Install

git clone https://github.com/jdonnerstag/py_gitfs.git
python -m venv .venv
.venv/scripts/activate
pip install -e .[dev]

## Documentation

- [PyFilesystem Wiki](https://www.pyfilesystem.org)
- [PyFilesystem Reference](https://docs.pyfilesystem.org/en/latest/reference/base.html)
