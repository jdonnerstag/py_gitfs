# coding: utf-8

__all__ = ["GITFS", "GitException"]

import os
import stat
import tempfile
import shutil
import urllib
import logging
import io
from datetime import datetime
from subprocess import Popen, PIPE
from pathlib import Path
from urllib.parse import SplitResult

from fs.osfs import OSFS


logger = logging.getLogger(name="git")

class GitException(Exception):
	pass

def execute_child_process(cmd: list[str], cwd: Path):
	"""
	Change the current working directory and execute the program
	"""

	cwd = str(cwd)
	logger.debug("Exec (cwd: %s): %s", cwd, " ".join(cmd))

	with Popen(
		cmd, cwd=cwd, shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE
	) as child:
		outs, errs = child.communicate()
		rtn_code = child.returncode
		rtn = None
		if outs:
			lines = outs.decode().splitlines()
			if lines:
				rtn = lines[0]

			for elem in lines:
				logger.debug(elem)

		if errs:
			lines = errs.decode().splitlines()
			for elem in lines:
				logger.debug(elem)

	if rtn_code:
		raise ChildProcessError(f"Execution failed. cmd={cmd}, error(s)={errs}")

	return rtn


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


__char_map_1 = "abcdefghijklmnopqrstupvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
__char_map_2 = "89abcdefghijklmnopqrstupvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567"

def map_access_token(token: str|None, map_1: str, map_2: str) -> str|None:
	if token is None:
		return None

	data = io.StringIO()
	for ch in token:
		i = map_1.find(ch)
		data.write(map_2[i])

	return data.getvalue()

def encode_access_token(token: str|None) -> str|None:
	return map_access_token(token, __char_map_1, __char_map_2)

def decode_access_token(token: str|None) -> str|None:
	return map_access_token(token, __char_map_2, __char_map_1)


class GITFS(OSFS):
	"""
	Construct an git filesystem for
	`PyFilesystem2 <https://pyfilesystem.org>`_

	:param str git_url: The got repository (url or directory)
	:param str branch: git branch name or revision string (default: 'master')
	:param str access_token: github (user) access token
	:param Datetime effective_date: Determine the last revision prior to the datetime (default: none)
	:param int evict_after: update (fetch + merge) the cloned repo latest after X secs (default: 3600 secs).
	:param int depth: number of revisions to clone (default: 1)
	:param bool create: If true, then create the directory (default: True)
	:param int create_mode: If the directory must be created, apply the directory permissions (rwxrwxrwx)
	:param bool expand_vars: If true, expand any environment vars, e.g. $HOME/...

	"""
	def __init__(self,
		git_url: str,
		branch: str = 'master',
		access_token: str|None = os.environ.get("GIT_ACCESS_TOKEN", None),
		local_dir: os.PathLike = tempfile.mkdtemp(),
		effective_date: datetime|None = None,
		evict_after: int|None = 3600,
		depth: int|None = 1,
		git_exe: str = "git",
		create: bool = True,
		create_mode: int = 0o777,
		expand_vars: bool = True,
		_test: bool = False
	):

		req = urllib.parse.urlsplit(git_url)
		assert req.scheme and req.scheme.lower().startswith("https")
		assert req.netloc
		assert req.path

		self.repo_name = req.path
		if self.repo_name.endswith(".git"):
			self.repo_name = os.path.basename(self.repo_name)[:-4]

		revision: str|None = None
		if req.query:
			params = urllib.parse.parse_qs(req.query)
			branch = params.get("branch", branch)
			revision = params.get("revision", revision)

		if branch.startswith("rev:"):
			revision = branch[4:]
			branch = None

		if branch:
			revision = None

		if revision:
			branch = None

		if req.username:
			access_token = req.username
			req = self.replace_access_token(req, None)
			git_url = req.geturl()

		# We want the access_token 'encrypted' also in-mem
		access_token = encode_access_token(access_token)

		assert local_dir
		assert os.path.isdir(local_dir), f"Not a valid local directory: {local_dir}"

		local_dir = os.path.expanduser(local_dir)
		local_dir = os.path.expandvars(local_dir)

		if not os.path.isabs(local_dir):
			local_dir = os.path.abspath(local_dir)

		local_dir = os.path.normpath(local_dir)

		git_exe = shutil.which(git_exe)
		assert os.path.exists(git_exe)

		self.git_url = req
		self.access_token = access_token
		self.branch = branch
		self.revision = revision
		self.local_dir = Path(local_dir)
		self.effective_date = effective_date
		self.evict_after = evict_after
		self.depth = depth
		self.git_exe = git_exe

		if not _test:
			self.update()

		super(GITFS, self).__init__(self.local_dir, create=create, create_mode=create_mode, expand_vars=expand_vars)

	def replace_access_token(self, req: SplitResult, token: str|None) -> SplitResult:
		"""
		Replace the access-token (or username/password) in the URL
		"""
		netloc = req.netloc.split("@", maxsplit=1)[-1]
		if token:
			netloc = f"{token}@{netloc}"
		return req._replace(netloc=netloc)

	def update(self):
		"""Checkout from git"""

		# Clone or refresh the local git repo
		git_dir = self.local_dir.joinpath(self.repo_name, ".git")
		if not git_dir.is_dir():
			self.git_clone(self.git_url)

		# Determine the revision, if an effective date was provided
		if self.effective_date and not self.revision:
			self.revision = self.determine_revision(self.effective_date, self.branch)

		# Either checkout branch or revision
		if self.revision:
			self.git_checkout_revision(self.revision)
		else:
			self.git_checkout_branch(self.branch)

	def git_exec(self, git_args: list[str], repo_parent: bool = False):
		"""Execute git applying the 'git_args' in the directory specified"""

		if repo_parent:
			cwd = self.local_dir
		else:
			cwd = self.local_dir.joinpath(self.repo_name)

		cmd = [self.git_exe] + git_args
		return execute_child_process(cmd, cwd)

	# We must be able to test it :(
	def _get_access_token(self) -> str:
		return decode_access_token(self.access_token)

	def git_clone(self, git_url: SplitResult|str):
		"""Clone the repo"""

		# Github does not support "git archive --remote=http://".

		if isinstance(git_url, str):
			git_url = urllib.parse.urlsplit(git_url)

		cwd = self.local_dir.joinpath(self.repo_name, ".git")
		if cwd.is_dir():
			raise GitException(f"Git: Local git repo already exists: {cwd}")

		access_token = self._get_access_token()
		req = self.replace_access_token(git_url, access_token)
		new_url = req.geturl()

		try:
			self.git_exec(["clone", new_url], True)
		except Exception as exc:
			raise GitException(f"Git: Unable to clone git repo: '{git_url}'") from exc

	def git_checkout_branch(self, branch: str):
		try:
			self.git_exec(["checkout", branch])
		except Exception as exc:
			raise GitException(f"Git: Failed to checkout branch: '{branch}'") from exc

	def git_checkout_revision(self, revision: str):
		try:
			self.git_exec(["reset", "--hard", revision])
		except Exception as exc:
			raise GitException(f"Git: Failed to checkout revision: '{revision}'") from exc

	def git_pull(self):
		"""Git Fetch and merge"""
		try:
			self.git_exec(["pull"])
		except Exception as exc:
			cwd = self.local_dir.joinpath(self.repo_name)
			raise GitException(f"Git: Failed to pull (update) git repo: '{cwd}'") from exc

	def determine_revision(self, effective_date: datetime, branch: None | str):
		"""Determine which revision was effective in the branch at that time"""

		# git rev-list -n 1 --before="2018-09-01 23:59:59" master
		# str() convert datetime nicely into "2018-09-01 23:59:59"
		date = str(effective_date)
		date = date.replace("9999-", "2099-")
		cmd = ["rev-list", "--max-count=1", f'--before="{date}"']

		if branch:
			cmd += [branch]

		try:
			return self.git_exec(cmd)
		except Exception as exc:
			raise GitException(f"Git: Unable to determine revision by date: '{effective_date}', branch: '{branch}'") from exc

	def current_branch(self) -> str:
		"""Determine the current branch name: git rev-parse --abbrev-ref HEAD

		Which is the same as 'git branch --show-current' since git 2.22
		"""

		cmd = ["rev-parse", "--abbrev-ref", "HEAD"]
		try:
			return self.git_exec(cmd)
		except Exception as exc:
			raise GitException(f"Git: Unable to determine current branch") from exc


	def current_revision(self, short: bool=True) -> str:
		"""Determine the current branch name: git rev-parse HEAD

		Which is the same as 'git branch --show-current' since git 2.22
		"""

		if short:
			cmd = ["rev-parse", "--short", "HEAD"]
		else:
			cmd = ["rev-parse", "HEAD"]

		try:
			return self.git_exec(cmd)
		except Exception as exc:
			raise GitException(f"Git: Unable to determine current revision") from exc

	def delete_local_clone(self):
		"""Local the local git clone (remove the directory)"""

		def del_rw(action, name, exc):
			# Delete readonly files
			os.chmod(name, stat.S_IWRITE)
			os.remove(name)

		shutil.rmtree(self.local_dir, onerror=del_rw)

	def __repr__(self):
		return _make_repr(
			self.__class__.__name__,
			self.git_url.geturl(),
			branch=(self.branch, None),
			revision=(self.revision, None),
		)
