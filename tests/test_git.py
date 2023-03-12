# coding: utf-8

import os
import stat
import unittest
import pathlib
import shutil
from datetime import datetime
from nose.plugins.attrib import attr

import tempfile
from dulwich.porcelain import NoneStream
from fs_gitfs import _git as git

# We are using this repo to run our tests on
git_repo = "https://github.com/jdonnerstag/py_gitfs.git"

# The master branch on the repo
master = "master"

# An alternative branch, which we want to checkout
do_not_delete_branch = "do_not_delete"
do_not_delete_branch_head_id = "35c87dcf7862087f32e10c5e68e8f890f9d8f727"

# We have a tag on the "do_not_delete" branch, which is not HEAD
my_test_release_tag = "my_test_release"
my_test_release_tag_id = "f39fd8c3faecb11b7e515b0e69a75338c01dae01"

# This is commit on "do_not_delete" branch is neither HEAD or
# does it have a tag.
commit_rev_id = "5d4b1242f13e341b83256e7087b5c6cde64507ce"


class GITTestCases:

	def setUp(self):
		self.local_dir = tempfile.mkdtemp()

	def tearDown(self):
		git.delete_repo(self.local_dir)


class Testing(GITTestCases, unittest.TestCase):
	def test_git_simple(self):
		git.export(self.local_dir, git_repo)
		assert git.origin_url(self.local_dir) == git_repo
		assert git.active_branch(self.local_dir) == master
'''
	def test_access_token(self):
		branch = master
		access_token = "abc"
		self.fs = GITFS(git_repo, local_dir=self.local_dir, password=access_token)
		assert access_token != self.fs.password
		assert access_token == self.fs._get_password()
		assert self.fs.is_detached() == False
		assert self.fs.current_branch() == branch

	def test_invalid_url(self):
		with self.assertRaises(GitException) as context:
			self.fs = GITFS("https://wrong.com/does_not_exist", local_dir=self.local_dir)

	def test_branch(self):
		branch = do_not_delete_branch
		self.fs = GITFS(git_repo, local_dir=self.local_dir, branch=branch)
		assert self.fs.branch == branch
		assert repr(self.fs) == f"GITFS('{git_repo}', branch='{branch}')"
		assert self.fs.is_detached() == False
		assert self.fs.current_branch() == branch

	def test_release_tag(self):
		branch = my_test_release_tag
		self.fs = GITFS(git_repo, local_dir=self.local_dir, branch=branch)
		assert self.fs.branch == branch
		assert repr(self.fs) == f"GITFS('{git_repo}', branch='{branch}')"
		assert self.fs.is_detached() == True	# Release-tag; not a branch => detached
		assert self.fs.current_branch() == "HEAD"

	def test_revision(self):
		revision = commit_rev_id
		self.fs = GITFS(git_repo, local_dir=self.local_dir, revision=revision)
		assert self.fs.branch == master
		assert self.fs.revision == revision
		assert self.fs.is_detached() == True
		assert self.fs.current_branch() == "HEAD"
		assert self.fs.current_revision(short=True) == revision

	def test_eff_date_param(self):
		effective_date = datetime(2023, 3, 5)
		self.fs = GITFS(git_repo, local_dir=self.local_dir, branch=commit_rev_id, effective_date=effective_date)

		revision = commit_rev_id
		assert self.fs.branch == my_test_release_tag
		assert self.fs.revision.startswith(revision)
		assert self.fs.is_detached() == True
		assert self.fs.current_branch() == "HEAD"
		assert self.fs.current_revision().startswith(revision)
		assert self.fs.current_revision(short=True) == revision

	def test_reuse_local_dir(self):
		self.fs = GITFS(git_repo, local_dir=self.local_dir, branch=master, auto_delete=False)
		self.fs.close()

		self.fs = GITFS(git_repo, local_dir=self.local_dir, branch=master, auto_delete=False)
		self.fs.close()

		with self.assertRaises(GitException) as context:
			GITFS(git_repo, local_dir=self.local_dir, branch=do_not_delete_branch, auto_delete=False)

		with self.assertRaises(GitException) as context:
			GITFS(git_repo, local_dir=self.local_dir, revision=commit_rev_id, auto_delete=False)

		self.fs = GITFS(git_repo, local_dir=self.local_dir, branch=master, auto_delete=False)
		self.fs.close()

	def test_my_new_clone_1(self):
		self.fs = GITFS(git_repo, local_dir=self.local_dir, _test=True)
		with self.fs.my_new_clone(
			git_repo,
			target=self.local_dir,
			errstream=NoneStream(),
			branch=master,
			depth=1) as repo:
			pass

		assert self.fs

	def test_my_new_clone_2(self):
		self.fs = GITFS(git_repo, local_dir=self.local_dir, _test=True)
		with self.fs.my_new_clone(
			git_repo,
			target=self.local_dir,
			errstream=NoneStream(),
			branch=do_not_delete_branch,
			depth=1) as repo:
			pass

	def test_my_new_clone_3(self):
		self.fs = GITFS(git_repo, local_dir=self.local_dir, _test=True)
		with self.fs.my_new_clone(
			git_repo,
			target=self.local_dir,
			errstream=NoneStream(),
			branch=do_not_delete_branch,
			single_commit=commit_rev_id,
			depth=1) as repo:
			pass

		assert self.fs

	# Test: git export into a FS, including an in-memory fs.
	# Test: opener with query parameter
	# Test: re-use existing already exported repo
'''
