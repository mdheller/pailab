import os
import sqlite3
import pickle
from datetime import datetime, timedelta
import json
import pailab.repo_objects as repo_objects
from pailab.repo_store import RepoInfoKey, _time_from_version
import pailab.repo as repo
from pailab.disk_handler import RepoObjectDiskStorage
from git import Repo
import logging
logger = logging.getLogger(__name__)


class RepoObjectGitStorage(RepoObjectDiskStorage):
    @staticmethod
    def is_git_repo(path):
        try:
            _ = Repo(path).git_dir
            return True
        except:
            return False

    def __init__(self, **kwargs):
        """Constructor

        Args:
            folder (str): directory used to store the objects in files as well as the sqlite database
            save_function (function, optional): Defaults to pickle_save. Function used to save the objects to disk.
            load_function (function, optional): Defaults to pickle_load. Function used to load the objects from disk.
        """
        super(RepoObjectGitStorage, self).__init__(**kwargs)
        if RepoObjectGitStorage.is_git_repo(self._main_dir):
            self._git_repo = Repo(self._main_dir)
        else:
            self._git_repo = Repo.init(self._main_dir)
        if not os.path.isfile(self._main_dir+'/.gitignore'):
            with open(self._main_dir+'/.gitignore', 'w') as f:
                f.write('.version.sqlite')

    def commit(self, message):
        check = self.check_integrity()
        if len(check) > 0:
            raise Exception(
                "Integrity check fails, cannot commit: " + str(check))

        untracked_files = self._git_repo.untracked_files

        if len(untracked_files) > 0 or self._git_repo.is_dirty():
            if len(untracked_files) > 0:
                self._git_repo.index.add(untracked_files)
            self._git_repo.index.commit(message)
        else:
            return "No commit: No untracked or modified files."

    def push(self, remote_name='origin'):
        remote = None
        for r in self._git_repo.remotes:
            if r.name == remote_name:
                remote = r
                break
        if remote is None:
            raise Exception('Remote ' + remote_name + ' does not exist.')
        remote.push()

    def _merge_from_db(self, sqlite_db_2):
        c = self._conn.cursor()
        c.execute('ATTACH DATABASE "' + sqlite_db_2 + '" AS db_2')
        statement = 'INSERT OR IGNORE INTO versions(name, version, file, uuid_time) SELECT name, version, file, uuid_time FROM db_2.versions;'
        c.execute(statement)
        statement = 'INSERT OR IGNORE INTO mapping(name, vcategory) SELECT name, category FROM db_2.mapping;'
        c.execute(statement)
        statement = 'INSERT OR IGNORE INTO modification_info(name, version, modifier, modifier_version) SELECT name, version, modifier, modifier_version FROM db_2.modification_info;'
        c.execute(statement)
        c.execute("DETACH DATABASE 'db_2';")

    def pull(self, remote_name='origin'):
        self._conn.close()
        remote = None
        for r in self._git_repo.remotes:
            if r.name == remote_name:
                remote = r
                break
        if remote is None:
            raise Exception('Remote ' + remote_name + ' does not exist.')
        self._conn.close()
        os.rename(self._sqlite_db_name(), self._sqlite_db_name() + '_old')
        try:
            remote.pull()
        except e:
            os.rename(self._sqlite_db_name() + '_old', self._sqlite_db_name())
            raise Exception('An error occured during pull: ' + (str(e)))
        self._merge_from_db(self._sqlite_db_name(),
                            self._sqlite_db_name() + '_old')
        os.remove(self._sqlite_db_name() + '_old')
