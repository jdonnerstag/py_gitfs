.. GITFS documentation master file, created by
   sphinx-quickstart on Sat Aug  5 12:55:45 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

GITFS
=====

GITFS is a `PyFilesystem interface
<https://docs.pyfilesystem.org/en/latest/reference/base.html>`_ to
git repository (storage).

As a PyFilesystem concrete class, GITFS allows you to work with git in the
same as any other supported filesystem.

Installing
==========

GITFS may be installed from pip with the following command::

    pip install fs-gitfs

This will install the most recent stable version.

Alternatively, if you want the cutting edge code, you can check out
the GitHub repos at https://github.com/jdonnerstag/py_gitfs


Introduction
============

Git is a version control system such that individual files are identified by their
file path (directory + file name), but always in the context of a revision (or branch).

Git is a distributed version control system, most often used with a single (master)
remote repository. To access files the (master) repository default approach is to
cloned it into a local directory.

This is also how the gitfs works. It clones or updates (pull and merge) a git repository
into a temporary directory. A temporary directory because the gitfs user may want
to access files from a specific branch or revision, and that may require to
checkout files.

Gitfs is a currently a readonly filesystem. Updates are not supported.


Opening a git Filesystem
========================

There are two options for constructing a :ref:`gitfs` instance. The simplest way
is with an *opener*, which is a simple URL like syntax. Here are initial examples::

    from fs import open_fs
    gitfs_local = open_fs('git://home/me/my_git_project', branch='main')
    gitfs_remote = open_fs('git://github.com/jdonnerstag/my_example_project', rev='ab23', access_token=GIT_ACCESS_TOKEN)

For more granular control, you may import the GITFS class and construct
it explicitly::

    from fs_gitfs import GITFS
    gitfs = GITFS('mybucket')

The local git repository will be created (clone) or updated (pull) upon either
of the calls (opener or explicit constructor).


GITFS Constructor
----------------

.. autoclass:: fs_gitfs.GITFS
    :members:


Authentication
==============

If you don't supply any credentials, then GITFS will use the access token
configured on your system. You may also specify it when creating the filesystem
instance. Here's how you would do that with an opener::

    gitfs = open_fs('git://<access token>@mybucket')

    which is the same as:
    gitfs = open_fs('git://mybucket', access_token='<access token>')

    Without explicit access_token argument, gitfs will apply the 'GIT_ACCESS_TOKEN'
    environment variable. Which is the same as:
    gitfs = open_fs('git://mybucket', access_token=os.environ['GIT_ACCESS_TOKEN'])


All arguments are also available with the constructor::

    gitfs = GITFS(
        'mybucket',
        access_token = <access token>
    )

.. note::

    It is not recommended to put credentials into your source code.
    Using credentials configured with the system, such as the GIT_ACCESS_TOKEN
    environment variable is preferred.


Opener Arguments:
=================

All arguments can later be accessed (read-only) via the GITFS object.

Arg: git_repo
-------------
  value: http-url or local path or filesystem

  The master git repository which will be used to clone the local repo, e.g.:
   - A http-url referring to a github repo
   - An pathlike object referring to an existing local git repository, which will be used as master
   - A PyFilesystem object (e.g. WrapFS) which refers (root directory) to an existing local git repository

Arg: branch
-----------
  value: <branch name> or rev:<revision value> (default: 'master')

Arg: access_token
-----------------
  value: <access token> (default: os.environ['GIT_ACCESS_TOKEN'])

Arg: local_dir
--------------
  value: <local directory pathlike> or <PyFilesystem> (default: os.mktemp())

  A local directory which will be the root directory for the cloned repo. If
  it doesn't exist, it'll be created (final path only).

  If a PyFilesystem object has been provided, the root directory of the filesystem
  will be the root of the cloned git repo.

  If the directory has been created with os.mktemp(), it will be auto-deleted at
  the end of the session

Arg: effective_date
-------------------
  value: a datetime object (default: <none>)

  Determine the revision based on the branch name and datetime provided.

Arg: evict_after
----------------
  value: <seconds duration> (default: 3600 secs == 1 hr)

  If the local git repo exists already, and the modify-time of the directory
  plus the duration, is smaller then 'now', then update the local repo
  (fetch and merge)

Arg: depth
----------
  value: <number> (default: 1)

  Often we don't need a full clone with all histories, but a specific revision only.
  A depth of 1 clones the revision files only.

  Use <none> to clone the full repo.


Additional Methods:
===================

Method: update()
----------------
  Update the local repo by executing a git fetch and merge


Method: branch(<branch name or revision>)
-----------------------------------------
  Checkout the files associated with the branch or revision


Method: revision_by_date(<branch>, <effective_date>)
----------------------------------------------------
  Determine the latest revision for <branch> just before <effective_date>.
  Invoke branch() to actually checkout the revision.


Method: clone_all()
-------------------
  Clone the full repository
  

More Information
================

See the `PyFilesystem Docs <https://docs.pyfilesystem.org>`_ for documentation on the rest of the PyFilesystem interface.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
