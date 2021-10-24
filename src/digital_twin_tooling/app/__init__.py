from flask import Flask
from flasgger import Swagger

app = Flask(__name__)
app.config["SECRET_KEY"] = 'something secret'
swagger = Swagger(app)

from digital_twin_tooling.app import project_api
from digital_twin_tooling.app import project_execution_api
