# coding: utf-8

from __future__ import unicode_literals

import unittest
import shutil

from nose.plugins.attrib import attr

from fs.test import FSTestCases
from fs_gitfs import GITFS
from fs.osfs import OSFS


class TestGITFS(FSTestCases, unittest.TestCase):
    """Test GITFS implementation from dir_path."""

    git_repo = "https://github.com/jdonnerstag/py_gitfs.git"
    local_dir = "C:\\Users\\jdonnerstag\\AppData\\Local\\Temp\\tmp61bvh65m"

    def make_fs(self):
        self._delete_contents()
        return GITFS(self.git_repo, local_dir=self.local_dir)

    def _delete_contents(self):
        shutil.rmtree(self.local_dir)

'''
@attr("slow")
class TestGITFSSubDir(FSTestCases, unittest.TestCase):
    """Test GITFS implementation from dir_path."""

    git_repo = "https://github.com/jdonnerstag/py_gitfs.git"

    def make_fs(self):
        self._delete_bucket_contents()
        self.s3.Object(self.bucket_name, "subdirectory").put()
        return GITFS(self.bucket_name, dir_path="subdirectory")

    def _delete_bucket_contents(self):
        response = self.client.list_objects(Bucket=self.bucket_name)
        contents = response.get("Contents", ())
        for obj in contents:
            self.client.delete_object(Bucket=self.bucket_name, Key=obj["Key"])


class TestGITFSHelpers(unittest.TestCase):
    def test_path_to_key(self):
        s3 = GITFS("foo")
        self.assertEqual(s3._path_to_key("foo.bar"), "foo.bar")
        self.assertEqual(s3._path_to_key("foo/bar"), "foo/bar")

    def test_path_to_key_subdir(self):
        s3 = GITFS("foo", "/dir")
        self.assertEqual(s3._path_to_key("foo.bar"), "dir/foo.bar")
        self.assertEqual(s3._path_to_key("foo/bar"), "dir/foo/bar")

    def test_upload_args(self):
        s3 = GITFS("foo", acl="acl", cache_control="cc")
        self.assertDictEqual(
            s3._get_upload_args("test.jpg"),
            {"ACL": "acl", "CacheControl": "cc", "ContentType": "image/jpeg"},
        )
        self.assertDictEqual(
            s3._get_upload_args("test.mp3"),
            {"ACL": "acl", "CacheControl": "cc", "ContentType": "audio/mpeg"},
        )
        self.assertDictEqual(
            s3._get_upload_args("test.json"),
            {"ACL": "acl", "CacheControl": "cc", "ContentType": "application/json"},
        )
        self.assertDictEqual(
            s3._get_upload_args("unknown.unknown"),
            {"ACL": "acl", "CacheControl": "cc", "ContentType": "binary/octet-stream"},
        )
'''

if __name__ == '__main__':
    unittest.main()