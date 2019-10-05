from flask import Flask, redirect, url_for
from flask import render_template
from flask import request
from flask import session
from flask import jsonify
import argparse
from itertools import chain
import pandas as pd

from ludwiglab.io_utils import write_pca_loadings_files
from ludwiglab.io_utils import save_probes_fs_mat
from ludwiglab.io_utils import write_probe_neighbors_files
from ludwiglab.io_utils import write_acts_tsv_file

from ludwiglab.log_utils import get_config_values_from_log
from ludwiglab.log_utils import get_requested_log_dicts
from ludwiglab.log_utils import make_log_dicts
from ludwiglab.log_utils import make_common_timepoint
from ludwiglab.log_utils import make_log_df

from ludwiglab.app_utils import make_form
from ludwiglab.app_utils import figs_to_imgs
from ludwiglab.app_utils import generate_terms
from ludwiglab.app_utils import get_log_dicts_values
from ludwiglab.app_utils import make_model_btn_name_info_dict
from ludwiglab.app_utils import make_requested
from ludwiglab.app_utils import make_template_dict
from ludwiglab.app_utils import load_configs_dict
from ludwiglab.app_utils import RnnlabAppError
from ludwiglab.app_utils import RnnlabEmptySubmission
from ludwiglab.model_figs import model_btn_name_figs_fn_dict
from ludwiglab.group_figs import group_btn_name_figs_fn_dict
from ludwiglab.model import Model
from ludwiglab import config

from ludwigcluster.logger import Logger
from chjildeshub.hub import Hub

app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
logger = Logger()


@app.route('/', methods=['GET', 'POST'])
def log():
    if not logger.log_path.is_file():
        logger.write_log()
    session.clear()
    config_names = make_requested(request, session, 'config_names', default=logger.manipulated_config_names)
    log_dicts = make_log_dicts(logger, config_names)
    table_headers = ['group_id', 'model_name'] + config_names + ['timepoint', 'num_saves']
    multi_group_btn_names = sorted(AppConfigs.MULTI_GROUP_BTN_NAME_INFO_DICT.keys())
    two_group_btn_names = sorted(AppConfigs.TWO_GROUP_BTN_NAME_INFO_DICT.keys())
    hub_mode = make_requested(request, session, 'hub_mode', default=GlobalConfigs.HUB_MODES[0])
    return render_template('log.html',
                           template_dict=make_template_dict(session),
                           log_dicts=log_dicts,
                           table_headers=table_headers,
                           multi_group_btn_names=multi_group_btn_names,
                           two_group_btn_names=two_group_btn_names,
                           hub_mode=hub_mode,
                           hub_modes=GlobalConfigs.HUB_MODES,
                           all_config_names=logger.all_config_names,
                           hostname=GlobalConfigs.HOSTNAME)


@app.route('/btns/<string:model_name>/', methods=['GET', 'POST'])
def btns(model_name):
    timepoints = logger.get_timepoints(model_name)
    timepoint = int(make_requested(request, session, 'timepoint', default=timepoints[-1]))
    if timepoint > timepoints[-1]:  # in case model doesn't have timepoint matching session timepoint
        timepoint = timepoints[-1]
        session['timepoint'] = [timepoint]
    hub_mode = make_requested(request, session, 'hub_mode', default=GlobalConfigs.HUB_MODES[0])
    model_btn_name_info_dict = make_model_btn_name_info_dict(model_name)
    btn_names = sorted(model_btn_name_info_dict.keys())
    return render_template('btns.html',
                           template_dict=make_template_dict(session),
                           btn_names=btn_names,
                           hub_mode=hub_mode,
                           hub_modes=GlobalConfigs.HUB_MODES,
                           model_name=model_name,
                           timepoint=timepoint,
                           timepoints=timepoints)


@app.route('/btns_action/<string:model_name>/', methods=['GET', 'POST'])
def btns_action(model_name):
    timepoint = int(make_requested(request, session, 'timepoint'))
    hub_mode = make_requested(request, session, 'hub_mode', default=GlobalConfigs.HUB_MODES[0])
    # imgs
    btn_name = request.args.get('btn_name')
    model_btn_name_info_dict = make_model_btn_name_info_dict(model_name)
    imgs_desc, needs_field_input = model_btn_name_info_dict[btn_name]
    if not needs_field_input:
        model = Model(model_name, timepoint)
        model.hub.switch_mode(hub_mode)
        figs = model_btn_name_figs_fn_dict[btn_name](model)
        imgs = figs_to_imgs(*figs)
        return render_template('imgs_model.html',
                               template_dict=make_template_dict(session),
                               model_name=model_name,
                               hub_mode=hub_mode,
                               timepoint=timepoint,
                               imgs=imgs,
                               imgs_desc=imgs_desc)
    else:
        return redirect(url_for('field',
                                model_name=model_name,
                                hub_mode=hub_mode,
                                btn_name=btn_name))




@app.route('/log_global_action/', methods=['GET', 'POST'])
def log_global_action():
    if request.args.get('delete_all') is not None:
        return redirect(url_for('delete_all'))
    elif request.args.get('summarize_all') is not None:
        return redirect(url_for('get_stats'))
    else:
        return 'rnnlab: Invalid request "{}".'.format(request.args)  # TODO put all such error messages into a formatted html


@app.route('/autocomplete/', methods=['GET'])
def autocomplete():
    return jsonify(json_list=session['autocomplete_list'])  # TODO cookie too large


@app.route('/which_hidden_btns/', methods=['GET'])
def which_hidden_btns():
    num_checkboxes_clicked = int(request.args.get('num_checkboxes_clicked'))
    if num_checkboxes_clicked == 2:
        result = 'both'
    elif num_checkboxes_clicked > 0:
        result = 'any'
    else:
        result = 'none'
    return result


@app.route('/field/<string:model_name>/<string:btn_name>', methods=['GET', 'POST'])
def field(model_name, btn_name):
    timepoint = int(make_requested(request, session, 'timepoint'))
    hub_mode = make_requested(request, session, 'hub_mode', default=GlobalConfigs.HUB_MODES[0])
    model = Model(model_name, timepoint)
    model.hub.switch_mode(hub_mode)
    # form
    btn_name_info_dict = make_model_btn_name_info_dict(model_name)
    imgs_desc, valid_type = btn_name_info_dict[btn_name]
    form = make_form(model, request, AppConfigs.DEFAULT_FIELD_STR, valid_type)
    # autocomplete
    if valid_type == 'probe':
        session['autocomplete_list'] = list(model.hub.probe_store.types)
    elif valid_type == 'cat':
        session['autocomplete_list'] = list(model.hub.probe_store.cats)
    elif valid_type == 'term':
        session['autocomplete_list'] = list(model.hub.train_terms.types)
    else:
        session['autocomplete_list'] = []
    # request
    if form.validate():
        field_input = form.field.data.split()
        figs = model_btn_name_figs_fn_dict[btn_name](model, field_input)
        imgs = figs_to_imgs(*figs)
        return render_template('imgs_model.html',
                               template_dict=make_template_dict(session),
                               model_name=model_name,
                               timepoint=timepoint,
                               hub_mode=hub_mode,
                               imgs=imgs,
                               imgs_desc=imgs_desc)
    else:
        return render_template('field.html',
                               template_dict=make_template_dict(session),
                               model_name=model_name,
                               timepoint=timepoint,
                               hub_mode=hub_mode,
                               form=form,
                               btn_name=btn_name)


@app.route('/generate/<string:model_name>', methods=['GET', 'POST'])
def generate(model_name):
    phrase = None
    timepoint = int(make_requested(request, session, 'timepoint'))
    hub_mode = make_requested(request, session, 'hub_mode', default=GlobalConfigs.HUB_MODES[0])
    model = Model(model_name, timepoint)
    model.hub.switch_mode(hub_mode)
    # task_id
    task_btn_str = make_requested(request, session, 'task_btn_str', default='Predict next terms')
    task_names = ['predict'] + model.task_names
    task_name = AppConfigs.TASK_BTN_STR_TASK_NAME_DICT[task_btn_str]
    task_id = task_names.index(task_name)
    # task_btn_strs
    task_btn_strs = [task_btn_str for task_btn_str in sorted(AppConfigs.TASK_BTN_STR_TASK_NAME_DICT.keys())
                     if AppConfigs.TASK_BTN_STR_TASK_NAME_DICT[task_btn_str] in task_names]
    # form
    input_str = 'Type phrase here'
    form = make_form(model, request, input_str, 'term')
    # make output_dict
    output_dict = {}
    if form.validate():
        phrase = form.field.data
        terms = phrase.split()
        for num_samples in AppConfigs.NUM_SAMPLES_LIST:
            output_dict[num_samples] = generate_terms(model, terms, task_id, num_samples=num_samples)
    return render_template('generate.html',
                           template_dict=make_template_dict(session),
                           model_name=model_name,
                           timepoint=model.timepoint,
                           form=form,
                           phrase=phrase,
                           output_dict=output_dict,
                           num_samples_list=AppConfigs.NUM_SAMPLES_LIST,
                           task_btn_strs=task_btn_strs)




@app.errorhandler(RnnlabEmptySubmission)  # custom exception
def handle_empty_submission(error):
    return render_template('error.html',
                           exception=error,
                           status_code=error.status_code,
                           template_dict=make_template_dict(session))


@app.errorhandler(RnnlabAppError)  # custom exception
def handle_empty_submission(error):
    return render_template('error.html',
                           exception=error,
                           status_code=error.status_code,
                           template_dict=make_template_dict(session))


@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html',
                           exception=error,
                           status_code=404,
                           template_dict=make_template_dict(session))


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodebug', action="store_false", default=True, dest='debug',
                        help='Use this for deployment.')
    return parser


if __name__ == "__main__":
    ap = arg_parser()
    argparse_namespace = ap.parse_args()
    app.run(port=5000, debug=argparse_namespace.debug, host='0.0.0.0')
