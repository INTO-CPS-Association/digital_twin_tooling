
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

app.config["PROJECT_BASE"] = "C:\\Users\\frdrk\\Documents\\into-cps-projects\\example-single_watertank\\DTP\\dtp-1"

@app.route('/')
def index():
    """Base uel.
    ---

    responses:
      200:
        description: Welcome

    """
    return "Welcome"


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
        if isinstance(selected_conf, list) and part.isdigit() and 0 <= int(part) < len(selected_conf):
            selected_conf = selected_conf[int(part)]
        else:
            if part in selected_conf:
                selected_conf = selected_conf[part]
            else:
                return None
    return selected_conf


def delete_config_element(conf, parts: list[str]):
    selected_conf = conf

    for idx, part in enumerate(parts):
        if isinstance(selected_conf, list) and part.isdigit() and 0 <= int(part) < len(selected_conf):
            del selected_conf[int(part)]
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
        if isinstance(selected_conf, list) and part.isdigit() and 0 <= int(part) < len(selected_conf):
            selected_conf = selected_conf[int(part)]
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
            insert_config_element(conf, parts, request.json)

            try:
                validate(conf, version='0.0.2')
            except jsonschema.exceptions.ValidationError as exc:
                abort(400, exc)

            with open(path, 'w') as fd:
                fd.write(yaml.dump(conf))

            return app.response_class(
                response=json.dumps(conf[elementpath]),
                status=200,
                mimetype='application/json'
            )


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
            # for idx, id in enumerate(parts):
            #     if id in selected_conf:
            #         selected_conf = selected_conf[id]
            #     else:

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
            # selected_conf = conf
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

# @app.route('/colors/<palette>/')
# def colors(palette):
#     """Example endpoint returning a list of colors by palette
#     This is using docstrings for specifications.
#     ---
#     parameters:
#       - name: palette
#         in: path
#         type: string
#         enum: ['all', 'rgb', 'cmyk']
#         required: true
#         default: all
#     definitions:
#       Palette:
#         type: object
#         properties:
#           palette_name:
#             type: array
#             items:
#               $ref: '#/definitions/Color'
#       Color:
#         type: string
#     responses:
#       200:
#         description: A list of colors (may be filtered by palette)
#         schema:
#           $ref: '#/definitions/Palette'
#         examples:
#           rgb: ['red', 'green', 'blue']
#     """
#     all_colors = {
#         'cmyk': ['cian', 'magenta', 'yellow', 'black'],
#         'rgb': ['red', 'green', 'blue']
#     }
#     if palette == 'all':
#         result = all_colors
#     else:
#         result = {palette: all_colors.get(palette)}
#
#     return jsonify(result)
