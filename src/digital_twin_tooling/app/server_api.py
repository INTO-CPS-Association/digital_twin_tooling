

from digital_twin_tooling.app import app
from flask import request

@app.route('/server/shutdown', methods=['GET'])
def get_server_shutdown():
    """List all schemas
    ---

    responses:
      200:
        description: Accepted shutdown

    """
    shutdown_server()

    return app.response_class(
            response="Shutting down..",
            status=200,
            mimetype='text/plain'
        )


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()