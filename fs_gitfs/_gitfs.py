# coding: utf-8

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

__all__ = ["GITFS"]

import contextlib
from datetime import datetime
import io
import itertools
import os
import tempfile
import mimetypes

import six
from six import text_type

from fs import ResourceType
from fs.osfs import OSFS
from fs.info import Info
from fs import errors
from fs.mode import Mode
from fs.subfs import SubFS
from fs.path import basename, dirname, forcedir, join, normpath, relpath
from fs.time import datetime_to_epoch


def _make_repr(class_name, *args, **kwargs):
    """
    Generate a repr string.

    Positional arguments should be the positional arguments used to
    construct the class. Keyword arguments should consist of tuples of
    the attribute value and default. If the value is the default, then
    it won't be rendered in the output.

    Here's an example::

        def __repr__(self):
            return make_repr('MyClass', 'foo', name=(self.name, None))

    The output of this would be something line ``MyClass('foo',
    name='Will')``.

    """
    arguments = [repr(arg) for arg in args]
    arguments.extend(
        "{}={!r}".format(name, value)
        for name, (value, default) in sorted(kwargs.items())
        if value != default
    )
    return "{}({})".format(class_name, ", ".join(arguments))


@six.python_2_unicode_compatible
class GITFS(OSFS):
    """
    Construct an git filesystem for
    `PyFilesystem <https://pyfilesystem.org>`_

    :param str bucket_name: The S3 bucket name.
    :param str dir_path: The root directory within the S3 Bucket.
        Defaults to ``"/"``

    """
    def __init__(self, git_url,
        branch = 'master',
        access_token = None,
        local_dir = tempfile.mkdtemp(),
        effective_date = datetime.now(),
        evict_after = 3600,
        depth = 1,
        create = True,
        create_mode = 0o777,
        expand_vars = True,
    ):

        self.branch = branch
        self.local_dir = local_dir
        self.effective_date = effective_date
        self.evict_after = evict_after
        self.depth = depth

        super(GITFS, self).__init__(self.local_dir, create=create, create_mode=create_mode, expand_vars=expand_vars)
