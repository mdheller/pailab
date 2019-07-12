"""This module creaes the data for plotting used by plot.py. The different methods return the respective data and information for plotting 
such as axes labels, titles, additional info which may be shown on hover in the plot encapsulated in a dictionary.
"""

import logging
import warnings
from pailab.ml_repo.repo import MLObjectType, MLRepo, NamingConventions  # pylint: disable=E0401,E0611
from pailab.ml_repo.repo_objects import RepoInfoKey, RawData  # pylint: disable=E0401
from pailab.ml_repo.repo_store import RepoStore, LAST_VERSION, FIRST_VERSION, _time_from_version  # pylint: disable=E0401

logger = logging.getLogger(__name__)


def _get_value_by_path(source, path):
    if not isinstance(path, list):
        p = path.split('/')
    else:
        p = path
    if len(p) == 0:
        return source
    if '[' in p[0]:
        tmp = p[0].split('[')
        name = tmp[0]
        index = int(tmp.split(']')[0])
        value = source[name][index]
    else:
        value = source[p[0]]
    if len(p) > 1:
        return _get_value_by_path(value, p[1:])
    return value


class _LabelChecker:
    """Checks wether a certain object and object version has a label
    """

    def __init__(self, ml_repo):
        self._labels = {}
        labels = ml_repo.get_names(MLObjectType.LABEL)
        for label in labels:
            l = ml_repo.get(label)
            if l.name in self._labels:
                self._labels[l.name][
                    l.version] = l.repo_info[RepoInfoKey.NAME]
            else:
                self._labels[l.name] = {
                    l.version: l.repo_info[RepoInfoKey.NAME]}

    def get_label(self, name, version):
        _name = name
        if len(_name.split('/')) == 1:
            _name = name + '/model'
        if name in self._labels.keys():
            if version in self._labels[name].keys():
                return self._labels[name][version]
        return None

    def get_model_and_version(label_name):
        """Returns a tuple of model and version if a label with label_name exists, otherwise it returns None.
        
        Args:
            label_name (str): Name of potential label
        """
        for model_name, v in self._labels.items():
            for version, label in v.items():
                if label == label_name:
                    return model_name, version
        return None

def get_measure_by_parameter(ml_repo, measure_names, param_name, data_versions=LAST_VERSION, training_param=False):
    """Returns for a (list of) measure(s) the measures and corresponding param values for a certain parameter 

    Args:
        ml_repo (MLRepo): the ml repo
        measure_names (str, list(str)): string or list of strings of measure names  
        param_name (str): name of parameter
        data_versions (version number, optional): Defaults to None. If not None, only values on measures on dta with this version number are used
    Returns:
        [dict]: dictionary of measure name to list of dictionaries containing the result, i.e. 
        model_version: version of model parameter
        param_version: version of the parameter of this data point
        param_name: the parameter value
        data_version: version of the underlying data
        train_data_version: version number of trainin data used to calibrate the model leading to this measure
        measure_version: version of measure
        value: measure value
    """
    label_checker = _LabelChecker(ml_repo)

    if isinstance(measure_names, str):
        measure_names = [measure_names]

    result_all = {}
    for measure_name in measure_names:
        data = str(NamingConventions.Data(NamingConventions.EvalData(
            NamingConventions.Measure(measure_name))))
        measures = ml_repo.get(measure_name, version=None, modifier_versions={data: data_versions})
        if not isinstance(measures, list):
            measures = [measures]
        model_name = NamingConventions.CalibratedModel(
            NamingConventions.Measure(measure_name)
        )
        if training_param:
            p_name = str(NamingConventions.TrainingParam(model_name))
        else:
            p_name = str(NamingConventions.ModelParam(model_name))
        train_data = ml_repo.get_names(MLObjectType.TRAINING_DATA)[0]
        model_name = str(model_name)
        # eval_name

        result = []
        n_warnings = 1
        for x in measures:
            p = ml_repo.get(
                p_name, version=x.repo_info[RepoInfoKey.MODIFICATION_INFO][p_name])
            try:
                param_value = _get_value_by_path(p.get_params(), param_name)
                # get train data version
                model = ml_repo.get(model_name, version = x.repo_info.modification_info[model_name])
                info = {'model_version': x.repo_info[RepoInfoKey.MODIFICATION_INFO][model_name],
                        param_name: param_value, 'param_version': p.repo_info[RepoInfoKey.VERSION],
                        'data_version': x.repo_info[RepoInfoKey.MODIFICATION_INFO][data],
                        'train_data_version': model.repo_info[RepoInfoKey.MODIFICATION_INFO][train_data],
                        'measure_version': x.repo_info[RepoInfoKey.VERSION], 'value': x.value}
                label = label_checker.get_label(
                    model_name, x.repo_info[RepoInfoKey.MODIFICATION_INFO][model_name])
                if label is not None:
                    info['model_label'] = label
                result.append(info)
            except:
                n_warnings += 1
                logger.warning('Could no retrieve parameter ' + p_name + ' for ' + p.repo_info.name + ', version ' + p.repo_info.version)
        if n_warnings > 1:
            warnings.warn('There are ' + str(n_warnings) + ' cases where the parameter could not be retrieved. See logging (logevel warning) for details.')
        result_all[measure_name] = result
    return result_all


def _get_obj_dict(ml_repo, objs, label_checker = None, category = None, _objs = None):
    if _objs is None:
        _objs = {}
    # first determine models (including their respective version) to be plotted
    def add_obj(obj_name, obj_version, objs_):
        if obj_name in objs_.keys():
            if isinstance(obj_version, list):
                objs_[obj_name].extend(obj_version)
            else: 
                objs_[obj_name].append(obj_version)
        else:
            if isinstance(obj_version, list):
                objs_[obj_name] = obj_version
            else:
                objs_[obj_name] = [obj_version]

    if objs is None:
        if label_checker is not None:
            logging.info('No model specified, use all labeled models.')
            for k, v in label_checker._labels.items():
                for w in v.keys():
                    add_obj(k, w, _objs)
        if category is not None:
            if isinstance(category, list):
                names = []
                for n in category:
                    names.extend(ml_repo.get_names(n))
            else:
                names = ml_repo.get_names(category)
            for n in names:
                _get_obj_dict(ml_repo, n, category = category, _objs = _objs)
    elif isinstance(objs, tuple):
        add_obj(objs[0], objs[1], _objs)
    elif isinstance(objs, str):
        if label_checker is not None:
            tmp = label_checker.get_model_and_version(objs)
            if tmp is not None:
                add_obj(tmp[0], tmp[1], _objs)
            else:
                add_obj(objs, LAST_VERSION, _objs)
        else:
            add_obj(objs, LAST_VERSION, _objs)
    elif isinstance(objs, dict):
        # check if some entry does contain a None entry->then the entry defines a label and must be replaced by model and version
        _get_obj_dict(ml_repo, [(k,v,) for k,v in objs.items()], label_checker, category, _objs)
    else:
        for m in objs:
            _get_obj_dict(ml_repo, m, label_checker, category, _objs)
    return _objs


def get_pointwise_model_errors(ml_repo, models, data, coord_name=None, data_version=LAST_VERSION, x_coord_name=None, start_index = 0, end_index = -1):
    label_checker = _LabelChecker(ml_repo)
    _data = data
    if isinstance(_data, str):
        _data = [data]

    #_models = get_model_dict(ml_repo, models)
    _models = _get_obj_dict(ml_repo, models, label_checker, MLObjectType.CALIBRATED_MODEL)
    ref_data = ml_repo.get(_data[0], version=data_version, full_object=False)
    coord = 0
    if coord_name is None:
        coord_name = ref_data.y_coord_names[0]
    if isinstance(coord_name, int):
        coord_name = ref_data.y_coord_names[coord_name]
    coord = ref_data.y_coord_names.index(coord_name)
    result = {'title': 'pointwise error (' + coord_name + ')', 'data': {}}
    if x_coord_name is None:
        result['x0_name'] = 'model-target  [' + coord_name + ']'
    else:
        if isinstance(x_coord_name, int):
            x_coord_name = ref_data.x_coord_names[x_coord_name]
        result['x0_name'] = x_coord_name
        result['x1_name'] = 'model-target  [' + coord_name + ']'

    for d in _data:
        ref_data = ml_repo.get(d, version=data_version, full_object=True)

        for m_name, m_versions in _models.items():
            if len(m_versions) == 1:
                m_versions = m_versions[0]
            tmp = m_name.split('/')[0]
            eval_data_name = str(
                NamingConventions.EvalData(data=d, model=tmp))
            logging.info('Retrieving eval data for model ' + tmp + ', versions ' +
                         str(m_versions) + ' and data ' + d + ', versions ' + str(data_version))
            eval_data = ml_repo.get(
                    eval_data_name, version=None, modifier_versions={m_name: m_versions, d: data_version}, full_object=True)
            if not isinstance(eval_data, list):
                eval_data = [eval_data]
            for eval_d in eval_data:
                error = ref_data.y_data[:, coord] - eval_d.x_data[:, coord]
                end = end_index
                if end > 0:
                    end = min(end, error.shape[0])
                tmp = {}
                if x_coord_name is None:
                    tmp['x0'] = error[start_index:end]
                else:
                    tmp['x1'] = error[start_index:end]
                    tmp['x0_name'] = x_coord_name
                    tmp['x0'] = ref_data.x_data[start_index:end,
                                                ref_data.x_coord_names.index(x_coord_name)]
                tmp['info'] = {d: str(data_version),
                               m_name: str(eval_d.repo_info[RepoInfoKey.MODIFICATION_INFO][m_name])}

                model_label = label_checker.get_label(
                    m_name, eval_d.repo_info[RepoInfoKey.MODIFICATION_INFO][m_name])
                if model_label is not None:
                    tmp['label'] = model_label

                result['data'][eval_data_name + ': ' +
                               str(eval_d.repo_info[RepoInfoKey.VERSION])] = tmp
    return result


def get_data(ml_repo, data, x0_coord_name, x1_coord_name=None, start_index = 0, end_index = -1):
    data_dict = _get_obj_dict(ml_repo, data, category=[MLObjectType.TRAINING_DATA, MLObjectType.TEST_DATA])
    result = {'title': 'data distribution', 'data': {}}
    result['data'] = {}
    if x1_coord_name is not None:
        result['x1_name'] = x1_coord_name
    x_coord = None
    y_coord = None
    for k, v in data_dict.items():
        ref_data = ml_repo.get(k, version=v, full_object=True)
        if not isinstance(ref_data, list):
            ref_data = [ref_data]
        for d in ref_data:
            if x_coord is None:
                if isinstance(x0_coord_name, str):
                    x_coord = d.x_coord_names.index(x0_coord_name)
                else:
                    x_coord = x0_coord_name
                    x0_coord_name = d.x_coord_names[x0_coord_name]
            if x1_coord_name is not None:
                y_coord = d.x_coord_names.index(x1_coord_name)
            tmp = {'info': {k:v}}
            tmp['x0'] = d.x_data[start_index:end_index, x_coord]
            if y_coord is not None:
                tmp['x1'] = d.x_data[:, y_coord]
            result['data'][d.repo_info[RepoInfoKey.NAME] + ': ' +
                           str(d.repo_info[RepoInfoKey.VERSION])] = tmp
    result['x0_name'] = x0_coord_name
    return result


def get_measure_history(ml_repo, measure_names):
    """Returns for a (list of) measure(s) the historic evolution of the measure  (using the order induced by the datetime encoded in the version number)

    Args:
        ml_repo (MLRepo): the ml repo
        measure_names (str, list(str)): string or list of strings of measure names (inlcuding full path) 

    Returns:

    """
    label_checker = _LabelChecker(ml_repo)

    if isinstance(measure_names, str):
        measure_names = [measure_names]

    result_all = {}
    for measure_name in measure_names:
        data = str(NamingConventions.Data(NamingConventions.EvalData(
            NamingConventions.Measure(measure_name))))
        measures = ml_repo.get(measure_name, version=(
            RepoStore.FIRST_VERSION, RepoStore.LAST_VERSION))  # , modifier_versions={data: data_versions})
        if not isinstance(measures, list):
            measures = [measures]
        model_name = NamingConventions.CalibratedModel(
            NamingConventions.Measure(measure_name)
        )
        model_name = str(model_name)
        train_data = ml_repo.get_names(MLObjectType.TRAINING_DATA)[0]

        # eval_name

        result = []
        for x in measures:
            info = {'model_version': x.repo_info[RepoInfoKey.MODIFICATION_INFO][model_name],
                    'data_version': x.repo_info[RepoInfoKey.MODIFICATION_INFO][data],
                    'train_data_version': x.repo_info[RepoInfoKey.MODIFICATION_INFO][train_data],
                    'value': x.value, 'datetime': _time_from_version(x.repo_info[RepoInfoKey.MODIFICATION_INFO][model_name])}
            label = label_checker.get_label(
                model_name, x.repo_info[RepoInfoKey.MODIFICATION_INFO][model_name])
            if label is not None:
                info['model_label'] = label
            result.append(info)

        result_all[measure_name] = result
    return result_all

import numpy as np
def project(ml_repo, model = None, labels = None, left = None, right=None,
         output_index = 0, n_steps = 100):
    if left is None or right is None:
        raise Exception('Please specify left and right points.')
    steps = [0.0 + float(x)/float(n_steps-1) for x in range(n_steps) ]
    # compute input for evaluation
    shape = (len(steps),)
    shape += left.shape
    x_data = np.empty(shape=shape)
    for i in range(len(steps)):
        x_data[i] = (1.0-steps[i])*left + steps[i]*right
    
    result = {}
    models = []
    if labels is None:
        labels = ml_repo.get_names(MLObjectType.LABEL)
        for l in labels:
            tmp = ml_repo.get(l)
            models.append((tmp.name, tmp.version, l))
    if model is None:
        tmp = ml_repo.get_names(MLObjectType.CALIBRATED_MODEL)
        if len(tmp) == 1:
            m  = ml_repo.get(tmp[0])
            models.append((tmp[0], m.repo_info.version, 'latest'))
    else:
        m  = ml_repo.get(model)
        model.append((model, m.repo_info.version, 'latest'))
        
    data = RawData(x_data, [""]*x_data.shape[1])
    for model in models:
        tmp = ml_repo.get(model[0], version=model[1], full_object=True)
        model_name = model[0].split('/')[0]
        model_def = ml_repo.get(model_name, tmp.repo_info.modification_info[model_name])
        eval_func = ml_repo.get(model_def.eval_function)
        tmp = eval_func.create()(tmp, data)
        if len(tmp.shape) == 1:
            result[model[2]] = tmp
        elif len(tmp.shape) == 2:
            result[model[2]] = tmp[:,output_index]
        
    return result