import unittest
from repo.repo_objects import RepoInfoKey  # pylint: disable=E0401
from repo.repo_objects import repo_object_init  # pylint: disable=E0401
import repo.repo as repo
import repo.repo_objects as repo_objects
import repo.memory_handler as memory_handler
import numpy as np


class TestClass:
    @repo_object_init(['mat'])
    def __init__(self, a, b, mat=None):
        self.a = a
        self._b = b
        self.mat = mat

    def a_plus_b(self):
        return self.a + self._b


class RepoInfoTest(unittest.TestCase):

    def test_repo_info(self):
        name = 'dummy'
        version = '1.0.2'
        repo_info = repo_objects.RepoInfo(**{'version': version, 'NAME': name})
        self.assertEqual(repo_info.name, 'dummy')
        self.assertEqual(repo_info['name'], 'dummy')
        self.assertEqual(repo_info['NAME'], 'dummy')
        self.assertEqual(repo_info[RepoInfoKey.NAME], 'dummy')
        repo_info.set_fields({RepoInfoKey.BIG_OBJECTS: {'dummy': 'dummy2'}})
        self.assertEqual(repo_info.name, 'dummy')
        self.assertEqual(repo_info.big_objects['dummy'], 'dummy2')
        self.assertEqual(repo_info.big_objects['dummy'], 'dummy2')
        repo_info[RepoInfoKey.NAME] = 'dummy2'
        self.assertEqual(repo_info.name, 'dummy2')
        repo_info['NAME'] = 'dummy2'
        self.assertEqual(repo_info['NAME'], 'dummy2')
        repo_info['name'] = 'dummy2'
        self.assertEqual(repo_info['NAME'], 'dummy2')
        self.assertEqual(repo_info['dummy'], None)
        repo_info_dict = repo_info.get_dictionary()
        self.assertEqual(repo_info_dict['name'], 'dummy2')
        # now test if dictionary contains only values for RepoInfoKeys
        for k in RepoInfoKey:
            self.assertEqual(repo_info_dict[k.value], repo_info[k])


class RepoObjectTest(unittest.TestCase):

    def test_repo_object_helper(self):
        orig = TestClass(5, 3)
        self.assertEqual(orig.a_plus_b(), 8)
        orig = TestClass(5, 3, repo_info={
                         'name': 'test'})  # pylint: disable=E1123
        tmp = repo_objects.create_repo_obj_dict(orig)
        new = repo_objects.create_repo_obj(tmp)
        self.assertEqual(orig.a_plus_b(), new.a_plus_b())
        # test if different constructor call work correctly after applying decorator
        orig = TestClass(5, b=3, repo_info={
                         'name': 'test'})  # pylint: disable=E1123
        tmp = repo_objects.create_repo_obj_dict(orig)
        new = repo_objects.create_repo_obj(tmp)
        self.assertEqual(orig.a_plus_b(), new.a_plus_b())

        orig = TestClass(**{'a': 5, 'b': 3},
                         repo_info={'name': 'test'})  # pylint: disable=E1123
        tmp = repo_objects.create_repo_obj_dict(orig)
        new = repo_objects.create_repo_obj(tmp)
        self.assertEqual(orig.a_plus_b(), new.a_plus_b())

    def test_repo_object(self):
        # initialize repo object from test class
        version = 5
        obj = TestClass(5, 3, repo_info={
                        'name': 'dummy', 'version': version})  # pylint: disable=E1123
        self.assertEqual(obj.repo_info.name, 'dummy')  # pylint: disable=E1101
        self.assertEqual(obj.repo_info.version,
                         version)  # pylint: disable=E1101
        repo_dict = obj.to_dict()  # pylint: disable=E1101
        self.assertEqual(repo_dict['a'], obj.a)
        self.assertEqual(repo_dict['_b'], obj._b)
        obj2 = TestClass(
            **repo_dict, repo_info={'name': 'dummy', 'version': version}, _init_from_dict=True)
        self.assertEqual(obj2.a, obj.a)
        self.assertEqual(obj2.a_plus_b(), obj.a_plus_b())


class RawDataTest(unittest.TestCase):
    def test_raw_data(self):
        pass


class RepoTest(unittest.TestCase):
    # test the repo together with a memory handler
    def test_repo_memory_handler(self):
        handler = memory_handler.RepoObjectMemoryStorage()
        numpy_handler = memory_handler.NumpyMemoryStorage()
        # init repository with sample in memory handler
        repository = repo.MLRepo(handler, numpy_handler, handler)
        test_obj = TestClass(5, 3, repo_info={
                             repo_objects.RepoInfoKey.CATEGORY.value: repo.MLObjectType.TRAINING_DATA.value, 'name': 'test_object'})

        # test simple add
        version = repository.add(test_obj, 'first test commit')
        self.assertEqual(
            test_obj.repo_info[repo_objects.RepoInfoKey.VERSION], 0)
        self.assertEqual(version, 0)

        # test simple get
        test_obj2 = repository.get('test_object')
        self.assertEqual(test_obj2.a_plus_b(), test_obj.a_plus_b())
        self.assertEqual(test_obj2.repo_info[repo_objects.RepoInfoKey.NAME],
                         test_obj.repo_info[repo_objects.RepoInfoKey.NAME])
        self.assertEqual(
            test_obj2.repo_info[repo_objects.RepoInfoKey.VERSION], 0)
        self.assertEqual(test_obj2.mat, None)

        # test if version is handled properly
        version = repository.add(test_obj2, 'second test commit')
        self.assertEqual(version, 1)

        # test if also the numpy object will b retrieved
        test_obj = TestClass(5, 3, np.zeros([100, 3]), repo_info={
                             repo.MLObjectType.TRAINING_DATA.value: 'test_data', 'name': 'test_object'})
        version = repository.add(test_obj)
        test_obj2 = repository.get('test_object', version, full_object=True)
        self.assertEqual(test_obj.mat.shape[0], test_obj2.mat.shape[0])
        self.assertEqual(test_obj.mat.shape[1], test_obj2.mat.shape[1])
        # test if latest version -1 is also working
        test_obj2 = repository.get('test_object', -1)
        self.assertEqual(test_obj2.repo_info[repo_objects.RepoInfoKey.VERSION],
                         test_obj.repo_info[repo_objects.RepoInfoKey.VERSION])
        # test if get_names works correctly
        names = repository.get_names(repo.MLObjectType.TRAINING_DATA.value)
        self.assertEqual(len(names), 1)
        self.assertEqual(names[0], 'test_object')
        # test if get get_history works
        history = repository.get_history('test_object')
        self.assertEqual(
            len(history), test_obj2.repo_info[repo_objects.RepoInfoKey.VERSION])


if __name__ == '__main__':
    unittest.main()
