# coding: utf-8

from __future__ import unicode_literals

import unittest
import pathlib
import shutil

from nose.plugins.attrib import attr

from fs.test import FSTestCases
from fs_gitfs import GITFS
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

	def destroy_fs(self, fs: GITFS):
		fs.delete_local_clone()
		super().destroy_fs(fs)


class Testing(unittest.TestCase):
	git_repo = "https://github.com/jdonnerstag/py_gitfs.git"

	def test_git_simple(self):
		local_dir = tempfile.mkdtemp()
		fs = None
		try:
			fs = GITFS(self.git_repo, local_dir=local_dir)
			assert fs.git_url.geturl() == "https://github.com/jdonnerstag/py_gitfs.git"
			assert fs.access_token is None
			assert fs.branch == "master"
			assert fs.revision is None
			assert fs.local_dir == pathlib.Path(local_dir)
			assert fs.effective_date is None
			assert fs.evict_after == 3600
			assert fs.depth == 1
			assert fs.git_exe is not None
			assert repr(fs) == "GITFS('https://github.com/jdonnerstag/py_gitfs.git', branch='master')"
		finally:
			if fs:
				fs.delete_local_clone()

	def test_access_token(self):
		local_dir = tempfile.mkdtemp()
		fs = None
		try:
			access_token = "abc"
			fs = GITFS(self.git_repo, local_dir=local_dir, access_token=access_token)
			assert access_token != fs.access_token
			assert access_token == fs._get_access_token()
		finally:
			if fs:
				fs.delete_local_clone()

	def test_invalid_url(self):
		local_dir = tempfile.mkdtemp()
		fs = None
		try:
			with self.assertRaises(ChildProcessError) as context:
				fs = GITFS("https://wrong.com/does_not_exist", local_dir=local_dir)
		finally:
			shutil.rmtree(local_dir)

	def test_branch_param(self):
		local_dir = tempfile.mkdtemp()
		fs = None
		try:
			branch = "test"
			fs = GITFS(self.git_repo, local_dir=local_dir, branch=branch)
			assert fs.branch == branch
			assert fs.revision is None
			assert repr(fs) == f"GITFS('https://github.com/jdonnerstag/py_gitfs.git', branch='{branch}')"
		finally:
			if fs:
				fs.delete_local_clone()

	def test_revision_param(self):
		pass

	def test_eff_date_param(self):
		pass

	def test_evict(self):
		pass

	def test_depth(self):
		pass
