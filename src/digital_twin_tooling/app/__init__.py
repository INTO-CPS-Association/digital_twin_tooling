from flask import Flask
from flasgger import Swagger
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = 'something secret'

if 'PROJECT_BASE' not in app.config:
    app.config["PROJECT_BASE"] = os.getcwd()

swagger = Swagger(app)

from digital_twin_tooling.app import project_api
from digital_twin_tooling.app import project_execution_api
from digital_twin_tooling.app import server_api
