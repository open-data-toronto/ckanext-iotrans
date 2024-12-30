from ckan.common import config
import ckan.tests.helpers as helpers
from ckan.logic import ValidationError
from contextlib import contextmanager
from shutil import rmtree
import os
import pytest
from ckan.logic import get_action, NotAuthorized


@contextmanager
def temp_directory(parent_dir: str):
    """temp_directory

    Context manager for a temporary file path that is removed (recursively) when the
    context exits.

    :param parent_dir: parent directory where to make a new `tmp` dir
    :type parent_dir: str
    :yield: str
    :rtype: None
    """
    path_name = os.path.join(parent_dir, "tmp")
    postfix = 0
    while os.path.exists(path_name):
        path_name = os.path.join(parent_dir, f"tmp{postfix}")
        postfix += 1

    os.makedirs(path_name)
    try:
        yield path_name
    finally:
        if os.path.exists(path_name):
            rmtree(path_name)


@pytest.fixture
def storage_path():
    return config.get("ckan.storage_path")


@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "datastore iotrans")
@pytest.mark.parametrize(
    "files",
    [
        # empty
        [],
        # one file
        ["file1.txt"],
        # multiple files
        ["file1.txt", "file2.txt"],
        # sub-directories
        ["./dir/file1.txt", "./dir/file2.txt", "file3.txt", "./other_dir"],
    ],
)
def test_deletes_files(files, storage_path):
    with temp_directory(storage_path) as tmp_dir:
        paths = [os.path.join(tmp_dir, file) for file in files]

        for path in paths:

            is_file = os.path.splitext(path)[1] != ""
            if is_file:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, "x")
            else:
                os.makedirs(path)
        assert all(os.path.exists(path) for path in paths)

        helpers.call_action("prune", path=tmp_dir)
        assert all(not os.path.exists(path) for path in paths)
        assert not os.path.exists(tmp_dir)

@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "datastore iotrans")
class TestRejectsPathsOutsideStoragePath:

    def test_rejects_relative_parents(self, storage_path):
        """
        Ensure users can't delete arbitrary system files/directories by `..`ing out of
        the storage path (e.g. delete the whole filesystem: path =/inet/ckan/../../)
        """
        path = os.path.join(storage_path, "..")

        # create a tmp dir 1 directory up and make sure prune doesn't let us delete it
        with temp_directory(path) as tmp_dir:
            with pytest.raises(ValidationError):
                # NOTE: important, we pass tmp_dir to prune instead of path so that if
                # this test fails, we don't clobber the entire storage_path
                helpers.call_action("prune", path=tmp_dir)

    def test_rejects_out_of_scope_abs_paths(self):
        """
        Ensure absolute paths outside if the storage path are also rejected
        """
        path = "/tmp"

        with temp_directory(path) as tmp_dir:
            with pytest.raises(ValidationError):
                # NOTE: important, we pass tmp_dir to prune instead of path so that if
                # this test fails, we don't clobber the entire `tmp` dir
                helpers.call_action("prune", path=tmp_dir)

@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "datastore iotrans")
def test_prune_checks_authentication(storage_path):
    with temp_directory(storage_path) as tmp_dir:
        with pytest.raises(NotAuthorized):
            get_action("prune")({}, {"path": tmp_dir})
