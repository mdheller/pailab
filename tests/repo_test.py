import unittest
import os
import numpy as np

from pailab import RepoInfoKey, MLObjectType, repo_object_init, RepoInfoKey, DataSet, RawData, MLRepo  # pylint: disable=E0401
from pailab.repo_objects import RepoInfo
import pailab.repo_objects as repo_objects
import pailab.memory_handler as memory_handler
import pailab.repo_store as repo_store
from pailab.job_runner.job_runner import SimpleJobRunner # pylint: disable=E0401
from pailab.numpy_handler_hdf import NumpyHDFStorage


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
        repo_info = RepoInfo({'version': version, 'NAME': name})
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
        orig = TestClass(5, 3, repo_info={  # pylint: disable=E1123
                         'name': 'test'})
        tmp = repo_objects.create_repo_obj_dict(orig)
        new = repo_objects.create_repo_obj(tmp)
        self.assertEqual(orig.a_plus_b(), new.a_plus_b())
        # test if different constructor call work correctly after applying decorator
        orig = TestClass(5, b=3, repo_info={  # pylint: disable=E1123
                         'name': 'test'})
        tmp = repo_objects.create_repo_obj_dict(orig)
        new = repo_objects.create_repo_obj(tmp)
        self.assertEqual(orig.a_plus_b(), new.a_plus_b())

        orig = TestClass(**{'a': 5, 'b': 3},  # pylint: disable=E1123
                         repo_info={'name': 'test'})  # pylint: disable=E1123
        tmp = repo_objects.create_repo_obj_dict(orig)
        new = repo_objects.create_repo_obj(tmp)
        self.assertEqual(orig.a_plus_b(), new.a_plus_b())

    def test_repo_object(self):
        # initialize repo object from test class
        version = 5
        obj = TestClass(5, 3,  # pylint: disable=E1123
                        repo_info={'name': 'dummy', 'version': version})  # pylint: disable=E1123
        self.assertEqual(obj.repo_info.name, 'dummy')  # pylint: disable=E1101
        self.assertEqual(obj.repo_info.version,  # pylint: disable=E1101
                         version)
        repo_dict = obj.to_dict()  # pylint: disable=E1101
        self.assertEqual(repo_dict['a'], obj.a)
        self.assertEqual(repo_dict['_b'], obj._b)
        obj2 = TestClass(
            **repo_dict, repo_info={'name': 'dummy', 'version': version}, _init_from_dict=True)
        self.assertEqual(obj2.a, obj.a)
        self.assertEqual(obj2.a_plus_b(), obj.a_plus_b())


class RawDataTest(unittest.TestCase):
    """Simple RawData objec tests
    """

    def test_validation(self):
        # test if validation works
        x_data = np.zeros([100, 2])

        # exception because number of coord_names does not equal number of x_coords
        with self.assertRaises(Exception):
            test_data = repo_objects.RawData(  # pylint: disable=W0612
                x_data, x_coord_names=[])  # pylint: disable=W0612
        # exception because number of y-coords does not equal number of x-coords
        y_data = np.zeros([99, 2])
        with self.assertRaises(Exception):
            test_data = repo_objects.RawData(  # pylint: disable=W0612
                x_data, x_coord_names=['x1', 'x2'], y_data=y_data, y_coord_names=['y1', 'y2'])
        # exception because number of y-coordnamess does not equal number of y-coords
        y_data = np.zeros([100, 2])
        with self.assertRaises(Exception):
            test_data = repo_objects.RawData(  # pylint: disable=W0612
                x_data, x_coord_names=['x1', 'x2'], y_data=y_data, y_coord_names=['y1'])

    def test_constructor(self):
        # simple construction
        x_data = np.zeros([100, 4])
        x_names = ['x1', 'x2', 'x3', 'x4']
        test_data = repo_objects.RawData(x_data, x_names)
        self.assertEqual(test_data.x_data.shape[0], x_data.shape[0])
        self.assertEqual(test_data.n_data, 100)
        # construction from array
        x_data = np.zeros([100])
        test_data = repo_objects.RawData(x_data, ['x1'])
        self.assertEqual(len(test_data.x_data.shape), 2)
        self.assertEqual(test_data.x_data.shape[1], 1)
        # construction from list
        test_data = repo_objects.RawData([100, 200, 300], ['x1'])
        self.assertEqual(test_data.x_data.shape[0], 3)
        self.assertEqual(test_data.x_data.shape[1], 1)

def eval_func_test(model, data):
    '''Dummy model eval function for testing
    
        Function retrns independent of data and model a simple numpy array with zeros
    Arguments:
        model {} -- dummy model, not used
        data {} -- dummy data, not used
    '''
    return np.zeros([10,1])

def train_func_test(model_param, training_param, data):
    '''Dummy model training function for testing
    
        Function retrns independent of data and model a simple numpy array with zeros
    Arguments:
        model_param {} -- dummy model parameter
        training_param {} -- dummy training parameter, not used
        data {} -- dummy trainig data, not used
    '''
    return TestClass(2,3, repo_info = {}) # pylint: disable=E1123

class RepoTest(unittest.TestCase):

    def _setup_measure_config(self):
        """Add a measure configuration with two measures (both MAX) where one measure just uses the coordinate x0
        """

        measure_config = repo_objects.MeasureConfiguration(
                                    [(repo_objects.MeasureConfiguration.MAX, ['y0']),
                                        repo_objects.MeasureConfiguration.MAX],
                                        repo_info={RepoInfoKey.NAME.value: 'measure_config'}
                                    )
        self.repository.add(measure_config, category=MLObjectType.MEASURE_CONFIGURATION, message = 'adding measure configuration')

    def _add_calibrated_model(self):
        dummy_model = TestClass(1,2, repo_info = {repo_objects.RepoInfoKey.NAME.value:'dummy_model'}) # pylint: disable=E1123
        self.repository.add(dummy_model, message = 'add dummy model', category=MLObjectType.CALIBRATED_MODEL)

    def setUp(self):
        '''Setup a complete ML repo with two different test data objetcs, training data, model definition etc.
        '''
        handler = memory_handler.RepoObjectMemoryStorage()
        numpy_handler = memory_handler.NumpyMemoryStorage()
        self.repository = MLRepo('doeltz', handler, numpy_handler, handler, None)
        job_runner = SimpleJobRunner(self.repository)
        self.repository._job_runner = job_runner
        #### Setup dummy RawData
        raw_data = repo_objects.RawData(np.zeros([10,1]), ['x0'], np.zeros([10,1]), ['y0'], repo_info = {repo_objects.RepoInfoKey.NAME.value: 'raw_1'})
        self.repository.add(raw_data, category=MLObjectType.RAW_DATA)
        raw_data = repo_objects.RawData(np.zeros([10,1]), ['x0'], np.zeros([10,1]), ['y0'], repo_info = {repo_objects.RepoInfoKey.NAME.value: 'raw_2'})
        self.repository.add(raw_data, category=MLObjectType.RAW_DATA)
        raw_data = repo_objects.RawData(np.zeros([10,1]), ['x0'], np.zeros([10,1]), ['y0'], repo_info = {repo_objects.RepoInfoKey.NAME.value: 'raw_3'})
        self.repository.add(raw_data, category=MLObjectType.RAW_DATA)
        ## Setup dummy Test and Training DataSets on RawData
        training_data = DataSet('raw_1', 0, None, 
                                    repo_info = {repo_objects.RepoInfoKey.NAME.value: 'training_data_1', repo_objects.RepoInfoKey.CATEGORY: MLObjectType.TRAINING_DATA})
        test_data_1 = DataSet('raw_2', 0, None, 
                                    repo_info = {repo_objects.RepoInfoKey.NAME.value: 'test_data_1',  repo_objects.RepoInfoKey.CATEGORY: MLObjectType.TEST_DATA})
        test_data_2 = DataSet('raw_3', 0, 2, 
                                    repo_info = {repo_objects.RepoInfoKey.NAME.value: 'test_data_2',  repo_objects.RepoInfoKey.CATEGORY: MLObjectType.TEST_DATA})
        self.repository.add([training_data, test_data_1, test_data_2])

        self.repository.add_eval_function('tests.repo_test', 'eval_func_test')
        self.repository.add_training_function('tests.repo_test', 'train_func_test')
        self.repository.add(TestClass(1,2, repo_info={repo_objects.RepoInfoKey.NAME.value: 'training_param', # pylint: disable=E1123
                                            repo_objects.RepoInfoKey.CATEGORY: MLObjectType.TRAINING_PARAM}))
        ## setup dummy model definition
        self.repository.add_model('model')
        # setup measure configuration
        self._setup_measure_config()
        # add dummy calibrated model
        self._add_calibrated_model()

    def test_adding_training_data_exception(self):
        '''Tests if adding new training data leads to an exception
        '''
        with self.assertRaises(Exception):
            test_obj = DataSet('raw_data', repo_info = {repo_objects.RepoInfoKey.CATEGORY: MLObjectType.TRAINING_DATA.value, 'name': 'test_object'})
            self.repository.add(test_obj)

    def test_version_increase(self):
        '''Test if updating an existing object increases the version
        '''
        obj = self.repository.get('raw_1')
        old_version = obj.repo_info[RepoInfoKey.VERSION]
        self.repository.add(obj)
        obj = self.repository.get('raw_1')
        new_version = obj.repo_info[RepoInfoKey.VERSION]
        self.assertEqual(old_version+1, new_version)

    def test_commit_increase_update(self):
        '''Check if updating an object in repository increases commit but does not change mapping
        '''
        obj = self.repository.get('raw_1')
        old_num_commits = len(self.repository.get_commits())
        old_version_mapping = self.repository.get('repo_mapping').repo_info[RepoInfoKey.VERSION]
        self.repository.add(obj)
        new_num_commits = len(self.repository.get_commits())
        new_version_mapping = self.repository.get('repo_mapping').repo_info[RepoInfoKey.VERSION]
        self.assertEqual(old_num_commits+1, new_num_commits)
        self.assertEqual(old_version_mapping, new_version_mapping)
        
    def test_commit_increase_add(self):
        '''Check if adding a new object in repository increases commit and does also change the mapping
        '''
        obj = DataSet('raw_data_1', 0, None, 
            repo_info={RepoInfoKey.NAME.value: 'test...', RepoInfoKey.CATEGORY: MLObjectType.TEST_DATA})
        old_num_commits = len(self.repository.get_commits())
        old_version_mapping = self.repository.get('repo_mapping').repo_info[RepoInfoKey.VERSION]
        self.repository.add(obj)
        new_num_commits = len(self.repository.get_commits())
        new_version_mapping = self.repository.get('repo_mapping').repo_info[RepoInfoKey.VERSION]
        self.assertEqual(old_num_commits+1, new_num_commits)
        self.assertEqual(old_version_mapping+1, new_version_mapping)
        commits = self.repository.get_commits()
        self.assertEqual(commits[-1].objects['test...'], 0)
        self.assertEqual(commits[-1].objects['repo_mapping'], new_version_mapping)

    def test_DataSet_get(self):
        '''Test if getting a DataSet does include all informations from the underlying RawData (excluding numpy data)
        '''
        obj = self.repository.get('test_data_1')
        raw_obj = self.repository.get(obj.raw_data)
        for i in range(len(raw_obj.x_coord_names)):
            self.assertEqual(raw_obj.x_coord_names[i], obj.x_coord_names[i])
        for i in range(len(raw_obj.y_coord_names)):
            self.assertEqual(raw_obj.y_coord_names[i], obj.y_coord_names[i])
    
    def test_DataSet_get_full(self):
        '''Test if getting a DataSet does include all informations from the underlying RawData (including numpy data)
        '''
        obj = self.repository.get('test_data_1', version = repo_store.RepoStore.LAST_VERSION, full_object = True)
        raw_obj = self.repository.get(obj.raw_data, version = repo_store.RepoStore.LAST_VERSION, full_object = True)
        for i in range(len(raw_obj.x_coord_names)):
            self.assertEqual(raw_obj.x_coord_names[i], obj.x_coord_names[i])
        for i in range(len(raw_obj.y_coord_names)):
            self.assertEqual(raw_obj.y_coord_names[i], obj.y_coord_names[i])
        self.assertEqual(raw_obj.x_data.shape[0], obj.x_data.shape[0])

        obj = self.repository.get('test_data_2', version = repo_store.RepoStore.LAST_VERSION, full_object = True)
        self.assertEqual(obj.x_data.shape[0], 2)
    
        obj = self.repository.get('training_data_1', version = repo_store.RepoStore.LAST_VERSION, full_object = True)
        self.assertEqual(obj.x_data.shape[0], 10)
    
    def test_repo_RawData(self):
        """Test RawData within repo
        """
        handler = memory_handler.RepoObjectMemoryStorage()
        numpy_handler = memory_handler.NumpyMemoryStorage()
        # init repository with sample in memory handler
        repository = MLRepo('doeltz', handler, numpy_handler, handler, None)
        job_runner = SimpleJobRunner(repository)
        repository._job_runner = job_runner
        raw_data = repo_objects.RawData(np.zeros([10, 1]), ['test_coord'], repo_info={  # pylint: disable=E0602
            repo_objects.RepoInfoKey.NAME.value: 'RawData_Test'})
        repository.add(raw_data, 'test commit', MLObjectType.RAW_DATA)
        raw_data_2 = repository.get('RawData_Test')
        self.assertEqual(len(raw_data.x_coord_names),
                         len(raw_data_2.x_coord_names))
        self.assertEqual(
            raw_data.x_coord_names[0], raw_data_2.x_coord_names[0])
        commits = repository.get_commits()
        self.assertEqual(len(commits), 1)
        self.assertEqual(len(commits[0].objects), 2)
        self.assertEqual(commits[0].objects['RawData_Test'], 0)
        
    def test_add_model_defaults(self):
        """test add_model using defaults to check whether default logic applies correctly
        """
        model_param = TestClass(3,4, repo_info={RepoInfoKey.NAME.value: 'model_param', RepoInfoKey.CATEGORY: MLObjectType.MODEL_PARAM.value}) # pylint: disable=E1123
        self.repository.add(model_param)
        training_param = TestClass(3,4, repo_info={RepoInfoKey.NAME.value: 'training_param', RepoInfoKey.CATEGORY: MLObjectType.TRAINING_PARAM.value}) # pylint: disable=E1123
        self.repository.add(training_param)
        self.repository.add_model('model1')
        model = self.repository.get('model1')
        self.assertEqual(model.eval_function, 'tests.repo_test.eval_func_test')
        self.assertEqual(model.training_function, 'tests.repo_test.train_func_test')
        self.assertEqual(model.training_param, 'training_param')
        self.assertEqual(model.model_param, 'model_param')
        
    def test_get_history(self):
        training_data_history = self.repository.get_history('training_data_1')
        self.assertEqual(len(training_data_history), 1)
        training_data = self.repository.get('training_data_1')
        self.repository.add(training_data)
        training_data_history = self.repository.get_history('training_data_1')
        self.assertEqual(len(training_data_history), 2)
        self.assertEqual(training_data_history[0]['repo_info']['version'], 0)
        self.assertEqual(training_data_history[1]['repo_info']['version'], 1)
        training_data_history = self.repository.get_history('training_data_1', version_start=1, version_end=1)
        self.assertEqual(len(training_data_history), 1)

    def test_run_eval_defaults(self):
        '''Test running evaluation with default arguments
        '''
        self.repository.run_evaluation()

    def test_run_train_defaults(self):
        '''Test running training with default arguments
        '''
        self.repository.run_training()

    def test_run_measure_defaults(self):
        self.repository.run_evaluation() # run first the evaluation so that there is at least one evaluation
        self.repository.run_measures()
    
    def test_repo_training_test_data(self):
        handler = memory_handler.RepoObjectMemoryStorage()
        numpy_handler = memory_handler.NumpyMemoryStorage()
        # init repository with sample in memory handler
        repository = MLRepo('doeltz', handler, numpy_handler, handler, None)
        job_runner = SimpleJobRunner(repository)
        repository._job_runner = job_runner
        training_data = RawData(np.zeros([10,1]), ['x_values'], np.zeros([10,1]), ['y_values'], repo_info = {repo_objects.RepoInfoKey.NAME.value: 'training_data'})
        repository.add(training_data, category=MLObjectType.TRAINING_DATA)
        
        training_data_2 = repository.get_training_data()
        self.assertEqual(training_data_2.repo_info[repo_objects.RepoInfoKey.NAME], training_data.repo_info[repo_objects.RepoInfoKey.NAME])
        test_data = RawData(np.zeros([10,1]), ['x_values'], np.zeros([10,1]), ['y_values'], repo_info = {repo_objects.RepoInfoKey.NAME.value: 'test_data'})
        repository.add(test_data, category=MLObjectType.TEST_DATA)
        
        test_data_2 = repository.get('test_data')
        self.assertEqual(test_data_2.repo_info[repo_objects.RepoInfoKey.NAME], test_data.repo_info[repo_objects.RepoInfoKey.NAME])
        test_data = RawData(np.zeros([10,1]), ['x_values'], np.zeros([10,1]), ['y_values'], repo_info = {repo_objects.RepoInfoKey.NAME.value: 'test_data_2'})
        repository.add(test_data, category = MLObjectType.TEST_DATA)
        
        test_data_2 = repository.get('test_data_2')
        self.assertEqual(test_data_2.repo_info[repo_objects.RepoInfoKey.NAME], test_data.repo_info[repo_objects.RepoInfoKey.NAME])
        commits = repository.get_commits()
        self.assertEqual(len(commits), 3)
        self.assertEqual(commits[1].objects['test_data'], 0)
        self.assertEqual(commits[1].objects['repo_mapping'], 1)
        self.assertEqual(commits[2].objects['test_data_2'], 0)
        self.assertEqual(commits[2].objects['repo_mapping'], 2)
        
        
import shutil
class NumpyHDFStorageTest(unittest.TestCase):
    def setUp(self):
        try:
            shutil.rmtree('test_numpy_hdf5')
            os.makedirs('test_numpy_hdf5')
        except OSError:
            os.makedirs('test_numpy_hdf5')
        self.store = NumpyHDFStorage('test_numpy_hdf5')
        
    def tearDown(self):
        try:
            shutil.rmtree('test_numpy_hdf5')
        except OSError:
            pass
        
    def test_add(self):
        # add martix
        test_data = np.full((1,5), 1.0)
        self.store.add('test_2d', '1', {'test_data': test_data})
        test_data_get = self.store.get('test_2d', '1')
        self.assertEqual(test_data_get['test_data'].shape, test_data.shape)
        self.assertEqual(test_data[0,0], test_data_get['test_data'][0,0])
        # add array
        test_data = np.full((1,), 1.0)
        self.store.add('test_1d', '1', {'test_data': test_data})
        test_data_get = self.store.get('test_1d', '1')
        self.assertEqual(test_data_get['test_data'].shape, test_data.shape)
        self.assertEqual(test_data[0], test_data_get['test_data'][0])
        # add 3d array
        test_data = np.full((1,5,5), 1.0)
        self.store.add('test_3d', '1', {'test_data': test_data})
        test_data_get = self.store.get('test_3d', '1')
        self.assertEqual(test_data_get['test_data'].shape, test_data.shape)
        self.assertEqual(test_data[0,0,0], test_data_get['test_data'][0,0,0])
        
    def test_append(self):
        # add martix
        test_data = np.full((1,5), 1.0)
        self.store.add('test_2d', '1', {'test_data': test_data})
        self.store.append('test_2d', '1', '2', {'test_data': np.full((1,5), 2.0)})
        self.store.append('test_2d', '2', '3', {'test_data': np.full((1,5), 3.0)})
        test_data_get = self.store.get('test_2d', '1')
        self.assertEqual(test_data_get['test_data'].shape, (1,5))
        self.assertEqual(test_data_get['test_data'][0,0], 1.0)
        test_data_get = self.store.get('test_2d', '2')
        self.assertEqual(test_data_get['test_data'].shape, (2,5))
        self.assertEqual(test_data_get['test_data'][0,0], 1.0)
        self.assertEqual(test_data_get['test_data'][1,0], 2.0)
        test_data_get = self.store.get('test_2d', '3')
        self.assertEqual(test_data_get['test_data'].shape, (3,5))
        self.assertEqual(test_data_get['test_data'][0,0], 1.0)
        self.assertEqual(test_data_get['test_data'][1,0], 2.0)
        self.assertEqual(test_data_get['test_data'][2,0], 3.0)

        # add array
        test_data = np.full((1,), 1.0)
        self.store.add('test_1d', '1', {'test_data': test_data})
        self.store.append('test_1d', '1', '2', {'test_data': np.full((1, ), 2.0)})
        self.store.append('test_1d', '2', '3', {'test_data': np.full((1, ), 3.0)})
        test_data_get = self.store.get('test_1d', '1')
        self.assertEqual(test_data_get['test_data'].shape, (1, ))
        self.assertEqual(test_data_get['test_data'][0], 1.0)
        test_data_get = self.store.get('test_1d', '2')
        self.assertEqual(test_data_get['test_data'].shape, (2, ))
        self.assertEqual(test_data_get['test_data'][0], 1.0)
        self.assertEqual(test_data_get['test_data'][1], 2.0)
        test_data_get = self.store.get('test_1d', '3')
        self.assertEqual(test_data_get['test_data'].shape, (3,))
        self.assertEqual(test_data_get['test_data'][0], 1.0)
        self.assertEqual(test_data_get['test_data'][1], 2.0)
        self.assertEqual(test_data_get['test_data'][2], 3.0)
        
        # add 3d array
        test_data = np.full((1,5,5), 1.0)
        self.store.add('test_3d', '1', {'test_data': test_data})
        test_data_get = self.store.get('test_3d', '1')
        self.assertEqual(test_data_get['test_data'].shape, test_data.shape)
        self.assertEqual(test_data[0,0,0], test_data_get['test_data'][0,0,0])

if __name__ == '__main__':
    unittest.main()
