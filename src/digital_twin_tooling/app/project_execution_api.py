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


@app.route('/projects/<projectname>/execution/configurations/<string:id>/run', methods=['POST'])
def project_execution_run(projectname, id):
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
    run_path = project_base / 'executions' / str(id)

    if not path.exists():
        abort(404, 'configurations does not exist')
    else:
        run_path.mkdir(exist_ok=True, parents=True)
        with open(path, 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)

            job_id = str(uuid.uuid4())
            with open(run_path / 'job_id.txt', 'w') as f:
                f.write(job_id)

            fmus = [path for path in request.args.get('fmus', "").split(",") if len(path) > 0]

            index = None

            for idx, config in enumerate(conf['configurations']):
                if 'id' in config and config['id'] == id:
                    index = idx

            if index is None:
                abort(404)

            tools.fetch_tools(conf, base, quite=True)
            project_mgmt.prepare(conf, index, job_id, run_path, None if len(fmus) == 0 else fmus, base_dir=base)
            project_mgmt.run(conf, index, run_path, base_dir=base)
            return project_execution_status(projectname, id)


@app.route('/projects/<projectname>/execution/configurations/<string:id>/stop', methods=['POST'])
def project_execution_stop(projectname, id):
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
    run_path = project_base / 'executions' / str(id)
    launchers.terminate_all_launcher(run_path)
    s = launchers.check_launcher_status_obj(run_path)
    return app.response_class(
        response=json.dumps(s),
        status=200,
        mimetype='application/json'
    )


@app.route('/projects/<string:projectname>/execution/configurations/<string:id>/status', methods=['GET'])
@app.route('/projects/<string:projectname>/execution/configurations/<string:id>', methods=['GET'])
def project_execution_status(projectname, id):
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
    run_path = project_base / 'executions' / str(id)
    s = launchers.check_launcher_status_obj(run_path)
    return app.response_class(
        response=json.dumps(s),
        status=200,
        mimetype='application/json'
    )
