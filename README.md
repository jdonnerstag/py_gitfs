# GITFS

GITFS is a [PyFilesystem](https://www.pyfilesystem.org/) interface to
git repositories (storage).

As a PyFilesystem concrete class, [GITFS](http://fs-gitfs.readthedocs.io/en/latest/) allows
you to work with git repository file in the same way as any other supported filesystem.

## Installing

You can install GITFS from pip as follows:

```
pip install fs-gitfs
```

## Opening a GITFS

Open an GITFS by explicitly using the constructor:

```python
from fs_gitfs import GITFS
gitfs = GITFS('myrepo')
```

Or with a FS URL:

```python
  from fs import open_fs
  gitfs = open_fs('git://myrepo')
```

## Downloading Files

To *download* files from a git repository, open a file on the S3
filesystem for reading, then write the data to a file on the local
filesystem. Here's an example that copies a file `example.mov` from
S3 to your HD:

```python
from fs.tools import copy_file_data
with gitfs.open('example.mov', 'rb') as remote_file:
    with open('example.mov', 'wb') as local_file:
        copy_file_data(remote_file, local_file)
```

Although it is preferable to use the higher-level functionality in the
`fs.copy` module. Here's an example:

```python
from fs.copy import copy_file
copy_file(gitfs, 'example.mov', './', 'example.mov')
```

## ExtraArgs


## Documentation

- [PyFilesystem Wiki](https://www.pyfilesystem.org)
- [GITFS Reference](http://fs-gitfs.readthedocs.io/en/latest/)
- [PyFilesystem Reference](https://docs.pyfilesystem.org/en/latest/reference/base.html)
