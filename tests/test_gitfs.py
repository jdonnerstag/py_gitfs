# coding: utf-8

from __future__ import unicode_literals

import os
import stat
import unittest
import pathlib
import shutil
from datetime import datetime
from nose.plugins.attrib import attr

from fs.test import FSTestCases
from fs_gitfs import GITFS, GitException, delete_repo
import tempfile


class TestGITFS(FSTestCases, unittest.TestCase):
	"""GITFS is based on OSFS and exposes a local directory. It should
	easily pass all standard tests
	"""

	git_repo = "https://github.com/jdonnerstag/py_gitfs.git"

	def make_fs(self):
		local_dir = tempfile.mkdtemp()

		# _test=True Do not clone or update the repo
		return GITFS(self.git_repo, local_dir=local_dir, _test=True)


class GITFSTestCases:
	git_repo = "https://github.com/jdonnerstag/py_gitfs.git"

	def setUp(self):
		self.local_dir = tempfile.mkdtemp()
		self.fs = None

	def tearDown(self):
		if self.fs:
			self.fs.close()

		self.fs = None
		delete_repo(self.local_dir)


class Testing(GITFSTestCases, unittest.TestCase):
	def test_git_simple(self):
		self.fs = GITFS(self.git_repo, local_dir=self.local_dir)
		assert self.fs.git_url.geturl() == "https://github.com/jdonnerstag/py_gitfs.git"
		assert self.fs.access_token is None
		assert self.fs.branch == "master"
		assert self.fs.local_dir == pathlib.Path(self.local_dir)
		assert self.fs.effective_date is None
		assert self.fs.git_exe is not None
		assert self.fs.auto_delete == True
		assert repr(self.fs) == "GITFS('https://github.com/jdonnerstag/py_gitfs.git', branch='master')"

	def test_access_token(self):
		access_token = "abc"
		self.fs = GITFS(self.git_repo, local_dir=self.local_dir, access_token=access_token)
		assert access_token != self.fs.access_token
		assert access_token == self.fs._get_access_token()

	def test_invalid_url(self):
		with self.assertRaises(GitException) as context:
			fs = GITFS("https://wrong.com/does_not_exist", local_dir=self.local_dir)

	def test_branch_param(self):
		branch = "test"
		self.fs = GITFS(self.git_repo, local_dir=self.local_dir, branch=branch)
		assert self.fs.branch == branch
		assert repr(self.fs) == f"GITFS('https://github.com/jdonnerstag/py_gitfs.git', branch='{branch}')"
		assert self.fs.is_detached() == False
		assert self.fs.current_branch() == branch

	def test_release_tag(self):
		branch = "my_test_release"
		self.fs = GITFS(self.git_repo, local_dir=self.local_dir, branch=branch)
		assert self.fs.branch == branch
		assert repr(self.fs) == f"GITFS('https://github.com/jdonnerstag/py_gitfs.git', branch='{branch}')"
		assert self.fs.is_detached() == True	# Release-tag; not a branch => detached
		assert self.fs.current_branch() == "HEAD"

	def test_revision_param(self):
		revision = "dc587fe"
		self.fs = GITFS(self.git_repo, local_dir=self.local_dir, revision=revision)
		assert self.fs.branch == "master"
		assert self.fs.revision == revision
		assert self.fs.is_detached() == True
		assert self.fs.current_branch() == "HEAD"
		assert self.fs.current_revision(short=True) == revision

	def test_eff_date_param(self):
		effective_date = datetime(2023, 3, 5)
		self.fs = GITFS(self.git_repo, local_dir=self.local_dir, branch="test", effective_date=effective_date)

		revision = "dc587fe"
		assert self.fs.branch == "test"
		assert self.fs.revision.startswith(revision)
		assert self.fs.is_detached() == True
		assert self.fs.current_branch() == "HEAD"
		assert self.fs.current_revision().startswith(revision)
		assert self.fs.current_revision(short=True) == revision

	def test_reuse_local_dir(self):
		self.fs = GITFS(self.git_repo, local_dir=self.local_dir, branch="master", auto_delete=False)
		self.fs.close()

		self.fs = GITFS(self.git_repo, local_dir=self.local_dir, branch="master", auto_delete=False)
		self.fs.close()

		with self.assertRaises(GitException) as context:
			GITFS(self.git_repo, local_dir=self.local_dir, branch="test", auto_delete=False)

		with self.assertRaises(GitException) as context:
			GITFS(self.git_repo, local_dir=self.local_dir, revision="dc587fe", auto_delete=False)

		self.fs = GITFS(self.git_repo, local_dir=self.local_dir, branch="master", auto_delete=False)
		self.fs.close()

	# Test: git export into a FS, including an in-memory fs.
	# Test: opener with query parameter
	# Test: re-use existing already exported repo
