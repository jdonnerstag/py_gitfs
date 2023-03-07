# coding: utf-8

__all__ = ["GITFS", "GitException", "delete_repo"]

import os
import stat
import tempfile
import shutil
from typing import Optional, Union
import urllib
import logging
import io
from datetime import datetime
from subprocess import Popen, PIPE
from pathlib import Path
from urllib.parse import SplitResult

from fs.osfs import OSFS

from dulwich.repo import Repo
from dulwich.client import HttpGitClient, get_transport_and_path
from dulwich.porcelain import clone as git_clone, NoneStream, open_repo_closing, find_unique_abbrev, active_branch, reset
from dulwich.porcelain import default_bytes_err_stream
from dulwich.porcelain import DEFAULT_ENCODING
from dulwich.config import Config, ConfigFile, StackedConfig
from dulwich.objectspec import parse_tree


logger = logging.getLogger(name="git")


def delete_repo(local_dir: str):
	def del_rw(action, name, exc):
		# Delete readonly files
		os.chmod(name, stat.S_IWRITE)
		os.remove(name)

	if os.path.exists(local_dir):
		shutil.rmtree(local_dir, onerror=del_rw)

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
	:param str branch: git branch name, release-tag or revision string (default: 'master')
	:param str access_token: github (user) access token
	:param Datetime effective_date: Determine the last revision prior to the datetime (default: none)
	:param bool create: If true, then create the directory (default: True)
	:param int create_mode: If the directory must be created, apply the directory permissions (rwxrwxrwx)
	:param bool expand_vars: If true, expand any environment vars, e.g. $HOME/...
	:param bool auto_delete: if true, the local directory gets deleted upon close()

	"""
	def __init__(self,
		git_url: str,
		*,
		branch: str = 'master',
		revision: str|None = None,
		username: str|None = None,
		password: str|None = os.environ.get("GIT_ACCESS_TOKEN", None),
		local_dir: os.PathLike = tempfile.mkdtemp(),
		effective_date: datetime|None = None,
		git_exe: str = "git",
		create: bool = True,
		create_mode: int = 0o777,
		expand_vars: bool = True,
		auto_delete: bool = True,
		_test: bool = False
	):

		req = urllib.parse.urlsplit(git_url)
		assert req.scheme and req.scheme.lower().startswith("https")
		assert req.netloc
		assert req.path

		self.repo_name = req.path
		if self.repo_name.endswith(".git"):
			self.repo_name = os.path.basename(self.repo_name)[:-4]

		if req.username:
			req = self.replace_credentials(req, None, None)

		# We want the access_token 'encrypted' also in-mem
		password = encode_access_token(password)

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
		self.username = username
		self.password = password
		self.branch = branch
		self.revision = revision
		self.local_dir = Path(local_dir)
		self.effective_date = effective_date
		self.git_exe = git_exe
		self.auto_delete = auto_delete

		if not _test:
			self.update()

		super(GITFS, self).__init__(self.local_dir, create=create, create_mode=create_mode, expand_vars=expand_vars)

	def repo_dir(self) -> Path:
		return self.local_dir.joinpath(self.repo_name)

	def replace_credentials(self, req: SplitResult, username: str|None, password: str|None) -> SplitResult:
		"""
		Replace username and/or password in the URL
		"""
		netloc = req.netloc.split("@", maxsplit=1)[-1]
		rtn = ""
		if username:
			rtn = username

		if password:
			if rtn:
				rtn += ":"

			rtn += password

		if rtn:
			rtn += "@"

		rtn += netloc
		return req._replace(netloc=rtn)

	def update(self):
		"""Checkout from git"""

		# Clone or refresh the local git repo
		git_dir = self.repo_dir().joinpath(".git")
		if git_dir.is_dir():
			# TODO Check that the repo URL is the same

			# TODO How do I know it is shallow (depth=1) and I need to fetch all?

			pass
		else:
			# We can clone and checkout in one go, except if it is a revision
			branch = None if self.effective_date or self.revision else self.branch
			self.git_clone(self.git_url, None)

		# Determine the revision, if an effective date was provided
		if self.effective_date:
			self.revision = self.determine_revision(self.effective_date, self.branch)

		# Note that git clone support branch names and release tags, but no
		# revisions. Whereas checkout also supports revisions.
		if self.revision:
			self.git_checkout_revision(self.revision)


	def git_exec(self, git_args: list[str], repo_parent: bool = False):
		"""Execute git applying the 'git_args' in the directory specified"""

		if repo_parent:
			cwd = self.local_dir
		else:
			cwd = self.repo_dir()

		cmd = [self.git_exe] + git_args
		return execute_child_process(cmd, cwd)

	# We must be able to test it :(
	def _get_access_token(self) -> str:
		return decode_access_token(self.access_token)

	def git_clone(self, git_url: SplitResult|str, branch: str|None):
		"""Clone the repo"""

		if isinstance(git_url, SplitResult):
			git_url = git_url.geturl()

		git_dir = self.local_dir.joinpath(self.repo_name, ".git")
		if git_dir.is_dir():
			raise GitException(f"Git: Local git repo already exists: {git_dir}")

		access_token = self._get_access_token()
		repo_dir = self.repo_dir()
		depth = None
		if branch:
			depth = 1

		try:
			# Make sure the repo gets properly closed and (files) get closed
			with git_clone(
				git_url,
				repo_dir,
				branch=branch,
				checkout=True,
				depth=depth,
				password=access_token,
				errstream=NoneStream()
			) as repo:

				index = repo.open_index()
				print(index.path)

		except Exception as exc:
			raise GitException(f"Git: Unable to clone git repo: '{git_url}'") from exc

	def git_checkout(self, branch: str):
		try:
			self.git_exec(["checkout", branch])
		except Exception as exc:
			raise GitException(f"Git: Failed to checkout branch: '{branch}'") from exc

	def find_sha1(self, sha1: str | bytes) -> bytes:
		if isinstance(sha1, str):
			sha1 = sha1.encode("utf-8")

		if len(sha1) >= 20:
			return sha1

		objs = []
		with open_repo_closing(self.repo_dir()) as repo:
			for obj in repo.object_store:
				if obj[:len(sha1)] == sha1:
					objs.append(obj)

		if not objs:
			raise GitException(f"Git object not found: '{sha1}'")
		elif len(objs) != 1:
			raise GitException(f"Found multiple Git objects: '{objs}'")

		return objs[0]


	def git_checkout_revision(self, revision: str):
		revision = self.find_sha1(revision)
		print(revision)
		reset(self.repo_dir(), "hard", revision)


	def git_archive(self, branch: str):
		# Note: github's implementation of git, does NOT SUPPORT it

		access_token = self._get_access_token()
		req = self.replace_access_token(self.git_url, access_token)
		new_url = req.geturl()

		try:
			self.git_exec(["archive", "--format=tar", f"--prefix={self.repo_name}/", f"--remote={new_url}", branch], True)
		except Exception as exc:
			raise GitException(f"Git: Failed to export branch: '{branch}'") from exc

	def determine_revision(self, effective_date: datetime, branch: None | str):
		"""Determine which revision was effective in the branch at that time"""

		# git rev-list -n 1 --before="2018-09-01 23:59:59" master
		# str() convert datetime nicely into "2018-09-01 23:59:59"
		date = str(effective_date)
		date = date.replace("9999-", "2099-")
		cmd = ["rev-list", "--max-count=1", f'--before="{date}"']

		if branch:
			cmd += [f'origin/{branch}']

		try:
			return self.git_exec(cmd)
		except Exception as exc:
			raise GitException(f"Git: Unable to determine revision by date: '{effective_date}', branch: '{branch}'") from exc

	def current_branch(self) -> str:
		"""Determine the current branch name: git rev-parse --abbrev-ref HEAD

		Which is the same as 'git branch --show-current' since git 2.22
		"""

		# For effective-date we clone/checkout the branch, then we determine the
		# revision number and checkout it out. Git checkout does print the message that
		# HEAD is now detached, but rev-parse is still providing the branch name.
		if self.effective_date:
			return "HEAD"

		try:
			branch = active_branch(self.repo_dir())
		except:
			return "HEAD"

		if isinstance(branch, list):
			branch = branch[0]

		if isinstance(branch, bytes):
			branch = branch.decode("utf-8", "ignore")

		return branch

	def current_revision(self, short: bool=True) -> str:
		"""Determine the current branch name: git rev-parse HEAD

		Which is the same as 'git branch --show-current' since git 2.22
		"""
		with open_repo_closing(self.repo_dir()) as r:
			return f"{find_unique_abbrev(r.object_store, r[r.head()].id)}"

	def is_detached(self) -> bool:
		"""Check whether the files are detached or related to a branch"""

		# For effective-date we clone/checkout the branch, then we determine the
		# revision number and checkout it out. Git checkout does print the message that
		# HEAD is now detached, but rev-parse is still providing the branch name.
		if self.effective_date:
			return True

		cmd = ["rev-parse", "--symbolic-full-name", "HEAD"]

		try:
			rtn = self.git_exec(cmd).strip()
			x = rtn == "HEAD"
		except Exception as exc:
			raise GitException(f"Git: Unable to determine current revision") from exc

		with open_repo_closing(self.repo_dir()) as r:
			rtn = r.refs.follow(b"HEAD")
			x2 = len(rtn[0]) < 2

		assert x == x2
		return x2

	def close(self):
		if self.auto_delete:
			delete_repo(self.local_dir)

		return super().close()

	def __repr__(self):
		return _make_repr(
			self.__class__.__name__,
			self.git_url.geturl(),
			branch=(self.branch, None),
			effective_date=(self.effective_date, None)
		)

	def my_new_clone(self,
		source,
		target=None,
		errstream=default_bytes_err_stream,
		origin: Optional[str] = "origin",
		depth: Optional[int] = None,
		branch: Optional[Union[str, bytes]] = None,
		single_commit: Optional[Union[str, bytes]] = None,
		config: Optional[Config] = None,
		**kwargs
	):
		"""Clone a local or remote git repository.
		"""
		if config is None:
			config = StackedConfig.default()

		if target is None:
			target = source.split("/")[-1]

		mkdir = not os.path.exists(target)

		(client, path) = get_transport_and_path(
			source, config=config, **kwargs)

		return self.my_new_client_clone(
			client,
			path,
			target,
			mkdir=mkdir,
			origin=origin,
			checkout=True,
			branch=branch,
			progress=errstream.write,
			depth=depth,
			single_branch=True,
			single_commit=single_commit
		)


	def my_new_client_clone(self, client, path, target_path, mkdir: bool = True, origin="origin",
			  checkout:bool=True, branch=None, progress=None, depth=None, single_branch: bool=False,
			  single_commit=None):
		"""Clone a repository."""
		from dulwich.refs import _set_default_branch, _set_head, _set_origin_head, _import_remote_refs
		from dulwich.client import LocalGitClient, SubprocessGitClient

		HEAD = b"HEAD"

		if mkdir:
			os.mkdir(target_path)

		try:
			target = Repo.init(target_path)
			assert target is not None
			assert branch

			encoded_path = path if isinstance(self, (LocalGitClient, SubprocessGitClient)) else client.get_url(path)
			encoded_path = encoded_path.encode(DEFAULT_ENCODING)

			encoded_origin = origin.encode(DEFAULT_ENCODING)
			config_section = (b"remote", encoded_origin)
			branch_ref = branch if single_branch else "*"
			if single_commit is None:
				encoded_fetch_refs = (f"+refs/heads/{branch_ref}:refs/remotes/{origin}/{branch_ref}")
			else:
				encoded_fetch_refs = (f"{single_commit}:refs/remotes/{origin}/{branch}")
			encoded_fetch_refs = encoded_fetch_refs.encode(DEFAULT_ENCODING)
			target_config = target.get_config()
			target_config.set(config_section, b"url", encoded_path)
			target_config.set(config_section, b"fetch", encoded_fetch_refs)
			target_config.write_to_path()

			ref_message = b"clone: from " + encoded_path
			result = client.fetch(path, target, progress=progress, depth=depth)
			_import_remote_refs(target.refs, origin, result.refs, message=ref_message)

			origin_head = result.symrefs.get(HEAD)
			origin_sha = result.refs.get(HEAD)
			if (origin_sha and not origin_head) or single_commit:
				# set detached HEAD
				target.refs[HEAD] = head_ref = origin_sha
			else:
				_set_origin_head(target.refs, encoded_origin, origin_head)
				encoded_branch = branch.encode(DEFAULT_ENCODING)
				head_ref = _set_default_branch(target.refs, encoded_origin, origin_head, encoded_branch, ref_message)

			# Update target head
			_set_head(target.refs, head_ref, ref_message)
			if checkout:
				tree = parse_tree(target, head_ref)
				target.reset_index(tree.id)

		except BaseException:
			if target is not None:
				target.close()
			if mkdir:
				shutil.rmtree(target_path)
			raise

		return target
