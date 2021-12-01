import uuid

from digital_twin_tooling.app import app
from pathlib import Path
from flask import abort
from flask import request
from digital_twin_tooling.project_mgmt import validate
import yaml
import jsonschema
import json
import shutil
from digital_twin_tooling import project_mgmt

def add_ids(conf):
    if 'configurations' in conf:
        confgis= conf['configurations']
        for c in confgis:
            if 'id' not in c:
                c.update({'id':str(uuid.uuid4())})
            if 'tasks' in c:
                for t in c['tasks']:
                    if 'id' not in t:
                        t.update({'id': str(uuid.uuid4())})

@app.route('/')
def index():
    """Base uel.
    ---

    responses:
      200:
        description: Welcome

    """
    return "Welcome"


@app.route('/project/schemas', methods=['GET'])
def get_project_schemas():
    """List all schemas
    ---

    responses:
      200:
        description: A list schemas for projects

    """
    with project_mgmt.get_schema(version="0.0.2") as stream:
        schema = yaml.load(stream, Loader=yaml.FullLoader)
        return app.response_class(
            response=json.dumps(schema),
            status=200,
            mimetype='application/json'
        )


@app.route('/projects', methods=['GET'])
def project_list():
    """List all projects
    ---

    responses:
      200:
        description: A list of projects

    """
    base = Path(app.config["PROJECT_BASE"])

    return json.dumps([f.parent.name for f in base.glob('*/projects.yml')])


@app.route('/projects/<projectname>', methods=['POST'])
def project_create(projectname):
    """Create a new project
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
      - name: projectdescription
        in: body
        type: string
        required: true
    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """

    base = Path(app.config["PROJECT_BASE"])
    path = base / projectname
    if path.exists():
        abort(405, "Already exists")
    else:
        path.mkdir(exist_ok=True, parents=True)

    return project_update(projectname)


@app.route('/projects/<projectname>/config', methods=['PUT'])
def project_update(projectname):
    """Create a new project
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
      - name: projectdescription
        in: body
        type: string
        required: true
    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """
    base = Path(app.config["PROJECT_BASE"])
    path = base / projectname

    if request.json:

        try:
            add_ids(request.json)
            validate(request.json, version='0.0.2')
        except jsonschema.exceptions.ValidationError as exc:
            abort(400, exc)

    if not path.exists():
        abort(404, "Project does not exist")

    if request.json:
        conf = request.json
    else:
        conf = {'version': '0.0.2'}

    with open(path / 'project.yml', 'w') as f:
        f.write(yaml.dump(conf))

    return app.response_class(
        response=json.dumps(conf),
        status=200,
        mimetype='application/json'
    )


@app.route('/projects/<projectname>', methods=['DELETE'])
def project_del(projectname):
    """Delete a project
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """
    base = Path(app.config["PROJECT_BASE"])
    path = base / projectname

    if not path.exists():
        abort(404)
    else:
        shutil.rmtree(str(path))

    return app.response_class(
        response="{}",
        status=200,
        mimetype='application/json'
    )


@app.route('/projects/<projectname>', methods=['GET'])
def project_get(projectname):
    """get a project
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true

    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """
    base = Path(app.config["PROJECT_BASE"])
    path = base / projectname / 'project.yml'

    if not path.exists():
        abort(404)
    else:
        with open(path, 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)
            return app.response_class(
                response=json.dumps(conf),
                status=200,
                mimetype='application/json'
            )


def resolve_config_element(conf, parts: list[str]):
    selected_conf = conf

    for idx, part in enumerate(parts):
        if isinstance(selected_conf, list):
            # for arrays we search by id if present otherwise we dont support it
            candidate = None
            for child in selected_conf:
                if 'id' in child and child['id'] == part:
                    candidate = child
                    break
            if candidate is None:
                return None
            else:
                selected_conf = candidate

        else:
            if part in selected_conf:
                selected_conf = selected_conf[part]
            else:
                return None
    return selected_conf


def delete_config_element(conf, parts: list[str]):
    selected_conf = conf

    for idx, part in enumerate(parts):
        if isinstance(selected_conf, list):
            # for arrays we search by id if present otherwise we dont support it
            for child in selected_conf:
                if 'id' in child and child['id'] == part:

                    if idx == len(parts) - 1:
                        selected_conf.remove(child)
                    else:
                        selected_conf = child
                    break
        else:
            if part in selected_conf:
                if idx == len(parts) - 1:
                    del selected_conf[part]
                else:
                    selected_conf = selected_conf[part]
            else:
                if idx == len(parts) - 1:
                    del selected_conf[part]
                else:
                    selected_conf[part] = {}
                selected_conf = selected_conf[part]


def insert_config_element(conf, parts: list[str], insert_value):
    selected_conf = conf

    for idx, part in enumerate(parts):
        if isinstance(selected_conf, list):
            # for arrays we search by id if present otherwise we dont support it
            for child in selected_conf:
                if 'id' in child and child['id'] == part:
                    selected_conf = child

                    if idx == len(parts) - 1:
                        new_value = insert_value
                        new_value['id'] = part
                        child.clear()
                        child.update(new_value)

                    break
        else:
            if part in selected_conf:
                if idx == len(parts) - 1:
                    selected_conf[part] = insert_value
                else:
                    selected_conf = selected_conf[part]
            else:
                if idx == len(parts) - 1:
                    selected_conf[part] = insert_value
                else:
                    selected_conf[part] = {}
                selected_conf = selected_conf[part]


@app.route('/projects/<projectname>/config/configurations', methods=['POST'])
def project_post_configurations_create(projectname):
    """Create a new configuration element
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
      - name: config
        in: body
        type: string
        required: true
    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """
    base = Path(app.config["PROJECT_BASE"])
    path = base / projectname / 'project.yml'

    if not path.exists():
        abort(404)
    else:

        new_data = {}
        if request.json:
            new_data = request.json

        if not 'id' in new_data:
            new_data.update({'id': str(uuid.uuid4())})

        with open(path, 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)
            if 'configurations' not in conf:
                conf['configurations'] = []

            conf['configurations'].append(new_data)

            try:
                add_ids(conf)
                validate(conf, version='0.0.2')
            except jsonschema.exceptions.ValidationError as exc:
                abort(400, exc)

            with open(path, 'w') as fd:
                fd.write(yaml.dump(conf))

            return app.response_class(
                response=json.dumps(new_data),
                status=200,
                mimetype='application/json'
            )


@app.route('/projects/<projectname>/config/configurations', methods=['PUT'])
def project_put_configurations_create(projectname):
    abort(401)


@app.route('/projects/<projectname>/config/<path:elementpath>', methods=['PUT', 'POST'])
def project_put_element(projectname, elementpath):
    """Put a new project element
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
      - name: elementpath
        in: path
        type: string
        required: true
      - name: config
        in: body
        type: string
        required: true
    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """

    base = Path(app.config["PROJECT_BASE"])
    path = base / projectname / 'project.yml'

    if not path.exists():
        abort(404)
    else:
        with open(path, 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)
            parts = str(elementpath).split('/')
            if len(parts) == 3 and parts[0] == "configurations" and parts[2] == "tasks":
                # this is creating a new task
                if request.method == 'POST':
                    config = resolve_config_element(conf, parts[0:-1])

                    if config is None:
                        abort(404)

                    if 'tasks' not in config:
                        config['tasks'] = []

                    new_data = request.json

                    # for key in new_data.keys():
                    new_task_id = str(uuid.uuid4())
                    new_data.update({'id': new_task_id})
                    elementpath = "/".join(parts) + '/' + new_task_id
                    # break
                    config['tasks'].append(new_data)
                else:
                    abort(401)
            else:
                insert_config_element(conf, parts, request.json)

            try:
                validate(conf, version='0.0.2')
            except jsonschema.exceptions.ValidationError as exc:
                abort(400, exc)

            with open(path, 'w') as fd:
                fd.write(yaml.dump(conf))

            return project_get_element(projectname, elementpath)


@app.route('/projects/<projectname>/config/<path:elementpath>', methods=['GET'])
def project_get_element(projectname, elementpath):
    """Get a project element
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
      - name: elementpath
        in: path
        type: string
        required: true
    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """
    base = Path(app.config["PROJECT_BASE"])
    path = base / projectname / 'project.yml'

    if not path.exists():
        abort(404)
    else:
        with open(path, 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)
            # selected_conf = conf
            parts = str(elementpath).split('/')
            selected_conf = resolve_config_element(conf, parts)
            if selected_conf is None:
                abort(400, elementpath + " not found")

            return app.response_class(
                response=json.dumps(selected_conf),
                status=200,
                mimetype='application/json'
            )


@app.route('/projects/<projectname>/config/<path:elementpath>', methods=['DELETE'])
def project_del_element(projectname, elementpath):
    """Delete a project element
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
      - name: elementpath
        in: path
        type: string
        required: true
    responses:
      200:
        description: List of project names
      405:
        description: already exists
    """
    base = Path(app.config["PROJECT_BASE"])
    path = base / projectname / 'project.yml'

    if not path.exists():
        abort(404)
    else:
        with open(path, 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)
            parts = str(elementpath).split('/')
            delete_config_element(conf, parts)

            with open(path, 'w') as fd:
                fd.write(yaml.dump(conf))

            return app.response_class(
                response=json.dumps(conf),
                status=200,
                mimetype='application/json'
            )


@app.route('/projects/<projectname>/prepare/config/<path:elementpath>', methods=['POST'])
def project_prepare_element(projectname, elementpath):
    """Prepare a config element
    ---
    parameters:
      - name: projectname
        in: path
        type: string
        required: true
      - name: elementpath
        in: path
        type: string
        required: true
    responses:
      200:
        description: List of project names
        examples:
            ddd:'fff'
      405:
        description: already exists
    """
    base = Path(app.config["PROJECT_BASE"])
    project_base = base / projectname
    path = project_base / 'project.yml'

    if not path.exists():
        abort(404)
    else:
        with open(path, 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)
            # selected_conf = conf
            parts = str(elementpath).split('/')
            selected_conf = resolve_config_element(conf, parts)
            if selected_conf is None:
                abort(400, elementpath + " not found")

            res = project_mgmt.prepare_task(conf, selected_conf, project_base, base_dir=base)

            return app.response_class(
                response=json.dumps(res),
                status=200,
                mimetype='application/json'
            )
