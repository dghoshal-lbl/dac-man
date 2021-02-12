# server.py
import os
import uuid
import glob
from pathlib import Path
from flask import Flask, flash, request, redirect
from flask import render_template, json, send_from_directory
from werkzeug.utils import secure_filename
from astropy.io import fits
import pandas as pd

from dacman import Executor, DataDiffer
import dacman
from dacman.plugins.default import DefaultPlugin
from flagging.flagging import sample_data, qa_flagging_app_deploy, combine_csv_files, clean_up


app = Flask(__name__, static_folder='../fits/build/static', template_folder='../fits/build')

UPLOAD_FOLDER = os.environ.get('DEDUCE_UPLOAD_FOLDER', '/home/deduce/workspace/deduce_fs/uploads')
RESULTS_FOLDER = os.environ.get('DEDUCE_RESULTS_FOLDER', '/home/deduce/workspace/deduce_fs/runs')
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/base/<path:filename>')
def base_static(filename):
    return send_from_directory(app.root_path + '/', filename)

@app.route('/api/fitsinfo')
def api_fits_info():
    hdul = fits.open('../spCFrame-b1-00161868.fits')
    output = hdul.info(output=False)
    return json.jsonify(output)

@app.route('/api/dacmantest')
def api_dacman_test():
    file1 = '../../../examples/data/simple/v0/file1'
    file2 = '../../../examples/data/simple/v1/file1'
    comparisons = [(file1, file2)]
    differ = DataDiffer(comparisons, executor=Executor.DEFAULT)
    differ.use_plugin(DefaultPlugin)
    results = differ.start()
    print(results)
    return json.jsonify(results)


@app.route('/api/fitschangesummary')
def api_fits_change_summary():
    json_data = open('./output/summary.json')
    data = json.load(json_data)
    return json.jsonify(data)


@app.route('/api/fits/plugin', methods = ['POST', 'GET'])
def run_fits_change_analysis():
    from pathlib import Path

    path_base = Path.home() / '/Users/sarahpoon/Documents/LBL/deduce/prototype/p6/dac-man/dacman/ui/exampledata/sdss_sample'

    # TODO this should be read from the request instead
    req_data = {
        'path': {
            'A': path_base / 'v5_6_5/6838/spCFrame-b1-00161868.fits',
            'B': path_base / 'v5_7_0/6838/spCFrame-b1-00161868.fits',
        },
        'metrics': [
            {
                'name': 'array_difference',
                'params': {
                    'extension': 1,
                }
            },
        ]
    }

    from dacman.plugins.fits import FITSUIPlugin

    comparator = FITSUIPlugin(metrics=req_data['metrics'])
    res = comparator.compare(req_data['path']['A'], req_data['path']['B'])

    res['outputs'] = []

    for output in ['a.png', 'b.png', 'delta.png']:
        path = Path(output)
        output_data = {
            'path_absolute': str(path.absolute),
            'filename': path.name,
            'filetype': path.suffix.replace('.', '', 1),
        }

    return json.jsonify(res)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# For Flagging
@app.route('/flagging/id', methods=['GET'])
def generate_project_id():
    project_id = str(uuid.uuid4())
    return json.jsonify({ 'project_id': project_id })

@app.route('/flagging/upload/<project_id>', methods=['POST'])
def upload_file(project_id):
    # check if the post request has the file part
    if 'upload_dataset' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['upload_dataset']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], project_id)
        
        if not os.path.exists(upload_path):
            os.mkdir(upload_path)

        file_path = os.path.join(upload_path, filename)
        file.save(file_path)

        data, data_total_shape = sample_data(file_path)
        return json.jsonify(
            {
                'project_id': project_id,
                'data_total_shape': list(data_total_shape),
                'data': data
            })

@app.route('/flagging/run/<project_id>', methods=['POST'])
def run_flagging(project_id):
    # check if the post request has the file part
    variable_details = request.get_json()

    datasets_dir = os.path.join(
        app.config['UPLOAD_FOLDER'],
        project_id
    )

    # TODO - check if all variables exist in all uploaded files

    processing_folder = qa_flagging_app_deploy(
        project_id,
        datasets_dir,
        variable_details,
        app.config['RESULTS_FOLDER']
    )

    output_csv_file, output_zip_file = combine_csv_files(processing_folder)

    output_csv_file = Path(output_csv_file)
    output_zip_file = Path(output_zip_file)

    data, data_total_shape = sample_data(output_csv_file)

    '''
    print({
        'folder_id': output_csv_file.parent.name,
        'csv_filename': output_csv_file.name,
        'zip_filename': output_zip_file.name,
        'data': data
    })
    '''

    clean_up(os.path.join(app.config['UPLOAD_FOLDER'], project_id))

    return json.jsonify({
        'data_total_shape': list(data_total_shape),
        'csv_filename': output_csv_file.name,
        'zip_filename': output_zip_file.name,
        'data': data
    })

@app.route('/flagging/download/<project_id>', methods=['POST'])
def download(project_id):
    #project_id = request.args.get('project_id')
    print(project_id)
    #print(request.get_json())
    folder_path = os.path.join(app.config['RESULTS_FOLDER'], project_id)
    print(glob.glob(os.path.join(folder_path, "*.csv.gz")))
    file_to_download = glob.glob(os.path.join(folder_path, "*.zip"))[0]
    file_to_download = os.path.basename(file_to_download)
    return send_from_directory(
        directory=folder_path,
        filename=file_to_download
    )

@app.route('/flagging/clean/<project_id>', methods=['POST'])
def clean(project_id):
    #clean_up(os.path.join(app.config['UPLOAD_FOLDER'], project_id))
    clean_up(os.path.join(app.config['RESULTS_FOLDER'], project_id))
    return "Data that belongs to project '%s' was deleted" % project_id

@app.route('/hello')
def hello():
    return 'Hello World!'

if __name__ == '__main__':
    app.run()
