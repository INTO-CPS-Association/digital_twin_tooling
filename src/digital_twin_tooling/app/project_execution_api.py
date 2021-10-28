from digital_twin_tooling.app import app
from pathlib import Path
from flask import abort
from flask import request
import yaml
import json
import uuid
from digital_twin_tooling import project_mgmt
from digital_twin_tooling import launchers
from digital_twin_tooling import tools


@app.route('/project/<projectname>/execution/configurations/<int:index>/run', methods=['POST'])
def project_execution_run(projectname, index):
    """Put a new project element
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
      - name: index
        in: path
        type: string
        required: true
      - name: fmus
        in: query
        type: string
        required: true
    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """
    # check if already running
    base = Path(app.config["PROJECT_BASE"])
    project_base = base / projectname
    path = project_base / 'project.yml'
    run_path = project_base / 'executions' / str(index)

    if not path.exists():
        abort(404, 'configurations does not exist')
    else:
        run_path.mkdir(exist_ok=True, parents=True)
        with open(path, 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)

            job_id = str(uuid.uuid4())
            with open(run_path / 'job_id.txt', 'w') as f:
                f.write(job_id)

            fmus = request.args.get('fmus')

            tools.fetch_tools(conf, base, quite=True)
            project_mgmt.prepare(conf, index, job_id, run_path, fmus, base_dir=base)
            project_mgmt.run(conf, index, run_path, base_dir=base)
            return project_execution_status(projectname,index)


@app.route('/project/<projectname>/execution/configurations/<int:index>/stop', methods=['POST'])
def project_execution_stop(projectname, index):
    """Put a new project element
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
      - name: index
        in: path
        type: string
        required: true
    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """
    # check if already running
    base = Path(app.config["PROJECT_BASE"])
    project_base = base / projectname
    run_path = project_base / 'executions' / str(index)
    launchers.terminate_all_launcher(run_path)
    s = launchers.check_launcher_status_obj(run_path)
    return app.response_class(
        response=json.dumps(s),
        status=200,
        mimetype='application/json'
    )


@app.route('/project/<string:projectname>/execution/configurations/<int:index>/status', methods=['GET'])
@app.route('/project/<string:projectname>/execution/configurations/<int:index>', methods=['GET'])
def project_execution_status(projectname, index):
    """Put a new project element
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
      - name: index
        in: path
        type: string
        required: true

    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """
    # check if already running
    base = Path(app.config["PROJECT_BASE"])
    project_base = base / projectname
    run_path = project_base / 'executions' / str(index)
    s = launchers.check_launcher_status_obj(run_path)
    return app.response_class(
        response=json.dumps(s),
        status=200,
        mimetype='application/json'
    )
