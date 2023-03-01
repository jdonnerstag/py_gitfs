# coding: utf-8
"""Defines the GITFS Opener."""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

__all__ = ["GITFSOpener"]

import os
import tempfile
from datetime import datetime

from fs.opener import Opener
from fs.opener.errors import OpenerError

from ._gitfs import GITFS


class GITFSOpener(Opener):
    protocols = ["git"]

    def open_fs(
        self,
        fs_url,  # type: Text
        parse_result,  # type: ParseResult
        writeable,  # type: bool
        create,  # type: bool
        cwd,  # type: Text
    ):

        git_url, _, branch = parse_result.resource.partition("/")

        if not git_url:
            raise OpenerError("invalid git url in '{}'".format(fs_url))

        branch = branch     # https://.../branch/<name>
        revision = branch   # https://.../revision/<name>

        access_token = git_url.determine_access_token(os.environ["GIT_ACCESS_TOKEN"])

        gitfs = GITFS(
            f"https://{git_url}",
            branch = parse_result.branch or 'master',
            access_token = access_token,
            local_dir = parse_result.params.get("local_dir", tempfile.mkdtemp()),
            effective_date = datetime.strptime(parse_result.params.get("effective_date"), "yyyymmddhhMMSS") or datetime.now(),
            evict_after = int(parse_result.params.get("evict_after", 3600)),
            depth = int(parse_result.params.get("depth", 1)),
        )

        return gitfs
