# coding: utf-8
'''Export a git repo

Git is mostly used for source code, but occassionally we are using git
for production data. To access git data in production, we need to export
them. Theoretically we don't need a clone with '.git' directory, and the easiest
way to achieve this would probably be 'git archive'. But unfortunately that is not
supported by github, one of the most used git repos.

Cloning a repo is reasonably fast, but while developing an application it wastes
precious time. Hence re-using an already existing local clone is supported.
Use optional eviction to automatically update the local clone after a while.
'''

import os
import stat
import shutil
from typing import Callable, Tuple
import logging
import io
from datetime import datetime, timedelta
from pathlib import Path

from dulwich.repo import Repo
from dulwich.client import HttpGitClient, get_transport_and_path
from dulwich.porcelain import clone as git_clone, NoneStream, open_repo_closing, find_unique_abbrev, active_branch, reset
from dulwich.porcelain import default_bytes_err_stream
from dulwich.porcelain import DEFAULT_ENCODING
from dulwich.config import Config, StackedConfig
from dulwich.objectspec import parse_tree
import dulwich
import dulwich.porcelain


logger = logging.getLogger(name="git")


class GitException(Exception):
	pass


def delete_repo(local_dir: str | os.PathLike):

	def del_rw(action, name, exc):
		# Also delete readonly files in .git/...
		os.chmod(name, stat.S_IWRITE)
		os.remove(name)

	if isinstance(local_dir, os.PathLike):
		local_dir = str(local_dir)

	if os.path.exists(local_dir):
		shutil.rmtree(local_dir, onerror=del_rw)


def directory_is_empty(directory: os.PathLike) -> bool:
    return not any(directory.iterdir())


def git_dir(directory: os.PathLike) -> os.PathLike:
	return directory.joinpath(".git")


def is_git_repo(directory: os.PathLike) -> bool:
	return git_dir(directory).exists()


def is_evicted(
		directory: os.PathLike,
		evict_after: timedelta | Callable[[os.PathLike, datetime, datetime], bool] | None
	) -> bool:

	if evicted is None:
		return False

	evicted = False
	evicted_date: datetime = datetime.now() - evict_after()
	repo_date = datetime.datetime.fromtimestamp(directory.stat().st_mtime)

	if isinstance(evict_after, timedelta):
		evicted = evicted_date < repo_date
	elif callable(evict_after):
		evicted = evict_after(directory, repo_date, evict_after)

	return evicted


def origin_url(local_repo: os.PathLike) -> str:
	with Repo(local_repo) as repo:
		# You should only using an existing clone with the same remote
		# TODO assert repo.remote("origin") == remote_repo

		config = repo.get_config()
		remote_name = config.get((b"remote", "origin"), b"url")
		return remote_name.decode("utf-8")


def export(
		local_repo: str | os.PathLike,
		remote_repo: str,
		branch: str | bytes = "master",
		revision: str | bytes | None = None,
		effective_date: datetime | None = None,
		evict_after: timedelta | Callable[[timedelta],bool] | None = None,
	):
	'''main function: Export a git repo'''

	local_repo, evicted = prepare_local_repo_dir(local_repo, remote_repo, evict_after)

	if effective_date:
		if revision:
			raise GitException(f"Use either 'effective_date' or 'revision': '{revision}', {effective_date}")

		revision = find_revision(local_repo, branch, effective_date)

	if revision:
		export_revision(local_repo, remote_repo, revision, evicted)
	else:
		export_branch(local_repo, remote_repo, branch, evicted)


def export_revision(local_repo: os.PathLike, remote_repo: str, revision: bytes, evicted: bool):
	if not revision:
		raise GitException(f"export_revision() requires a valid revision: '{revision}'")

	if evicted:
		my_new_clone(str(local_repo), revision=revision, checkout=False)

	# Make sure we have long (40 chars) hash
	revision = find_sha1(local_repo, revision)
	dulwich.porcelain.reset(str(local_repo), "hard", revision)


def find_sha1(local_repo: os.PathLike, sha1: str | bytes) -> bytes:
	if isinstance(sha1, str):
		sha1 = sha1.encode("utf-8")

	if len(sha1) >= 20:
		return sha1

	objs = []
	with open_repo_closing(str(local_repo)) as repo:
		for obj in repo.object_store:
			if obj[:len(sha1)] == sha1:
				objs.append(obj)

	if not objs:
		raise GitException(f"Git object not found: '{sha1}'")
	elif len(objs) != 1:
		raise GitException(f"Found multiple Git objects: '{objs}'")

	return objs[0]


def find_revision(local_repo: os.PathLike, branch: str | bytes, effective_date: datetime) -> bytes:
	if not branch:
		raise GitException(f"find_revision() requires a valid branch name: '{branch}'")

	if isinstance(branch, str):
		branch = branch.encode("utf-8")

	with Repo(str(local_repo)) as repo:
		for entry in repo.get_walker(include=[repo[c].id for c in branch]):
			if entry.date < effective_date:
				return entry.commit.id

	raise GitException(f"Failed to find revision: {local_repo}, {branch}, {effective_date}")


def active_branch(local_repo: Repo | os.PathLike) -> str:
	if isinstance(local_repo, os.PathLike):
		local_repo = str(local_repo)

	if isinstance(local_repo, str):
		with Repo(local_repo) as repo:
			branch = dulwich.porcelain.active_branch(repo.path)

	elif isinstance(local_repo, Repo):
		branch = dulwich.porcelain.active_branch(local_repo.path)

	if isinstance(branch, bytes):
		branch = branch.decode("utf-8", "ignore")

	return branch


def export_branch(local_repo: os.PathLike, remote_repo: str, branch: str | bytes, evicted: bool):
	if not branch:
		raise GitException(f"export_branch() requires a valid branch name: '{branch}'")

	if evicted:
		my_new_clone(remote_repo, str(local_repo), branch=branch, depth=1, close=True)
		return

	if is_git_repo(local_repo):
		branch_name = active_branch(local_repo)
		if branch_name == branch:
			return

	# It is possible to clone just a single branch. Hence the
	# branch may not be available locally yet.

	# 'branch' can be a branch or tag name
	local_branches = dulwich.porcelain.branch_list(str(local_repo))
	if branch not in local_branches:
		my_new_clone(remote_repo, str(local_repo), branch=branch, depth=1, close=True)
		return

	# Checkout
	dulwich.porcelain.reset(str(local_repo), "hard", b"HEAD")


def prepare_local_repo_dir(
		local_repo: str | os.PathLike,
		remote_repo: str,
		evict_after: timedelta | Callable[[timedelta],bool] | None = None
	) -> Tuple[os.PathLike, bool]:

	if isinstance(local_repo, str):
		local_repo = Path(local_repo)

	if not local_repo.is_dir():
		raise GitException(f"Directory does not exist: '{local_repo}'")

	evicted = True

	if not directory_is_empty(local_repo):
		is_existing_repo = is_git_repo(local_repo)
		if not is_existing_repo:
			raise GitException(f"Not a git local repo: '{local_repo}'")

		origin = origin_url(local_repo)
		if origin != remote_repo:
			raise GitException(f"Existing local repo has different origin: '{origin}' != '{remote_repo}'")

		evicted = is_evicted(local_repo, evict_after)

	return local_repo, evicted

###################

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


def current_revision(self, short: bool=True) -> str:
	"""Determine the current branch name: git rev-parse HEAD

	Which is the same as 'git branch --show-current' since git 2.22
	"""
	with open_repo_closing(self.repo_dir()) as r:
		return f"{find_unique_abbrev(r.object_store, r[r.head()].id)}"


def my_new_clone(
	source: str,
	target: str = None,
	errstream = NoneStream(),
	origin: str = "origin",
	depth: int | None = None,
	branch: None | str | bytes = None,
	single_commit: None | str | bytes = None,
	config: Config = StackedConfig.default(),
	close=False,
	**kwargs
):
	"""Clone a local or remote git repository.

	This is a copy of dulwich.porcelain.clone(), except that it is calling
	my extended cloning function.
	"""

	if target is None:
		target = source.split("/")[-1]

	mkdir = not os.path.exists(target)

	if "password" not in kwargs:
		password = os.environ.get("GIT_PASSWORD", None)
		if password:
			kwargs["password"] = password

	client, path = get_transport_and_path(source, config=config, **kwargs)

	rtn = my_new_client_clone(
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

	# Used for eviction
	Path(target).touch()

	if close:
		rtn.close()
		
	return rtn


def my_new_client_clone(
		client,
		path,
		target_path,
		mkdir: bool = True,
		origin="origin",
		checkout:bool=True,
		branch=None,
		progress=None,
		depth=None,
		single_branch: bool=False,
		single_commit=None
	):
	"""Clone a repository.

	This is basically copy & paste from dulwich.client.clone(), except that it supports
	the --single_branch option.
	"""
	from dulwich.refs import _set_default_branch, _set_head, _set_origin_head, _import_remote_refs
	from dulwich.client import LocalGitClient, SubprocessGitClient

	HEAD = b"HEAD"

	if mkdir:
		os.mkdir(target_path)

	try:
		target = Repo.init(target_path)
		assert target is not None
		assert branch

		encoded_path = path if isinstance(client, (LocalGitClient, SubprocessGitClient)) else client.get_url(path)
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
