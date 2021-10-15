from os import environ
from testcontainer_python_rabbitmq import RabbitMQContainer


class RemoteRabbitMQContainer:
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def __del__(self):
        pass

    def get_url(self):
        return f"http://localhost:15672"

    def get_amqp_port(self):
        return 5672

    def get_container_host_ip(self):
        return "localhost"

    def start(self):
        pass

    def stop(self):
        pass


class RabbitMQContainerCI:
    def __init__(self, **kwargs):
        if environ.get('CI') and not environ.get('RUNNER_OS') == 'Linux':
            print("Running with rabbitmq in CI mode. Please ensure the server is ready")
            self.proxy = RemoteRabbitMQContainer()
        else:
            self.proxy = RabbitMQContainer(**kwargs)

    def __enter__(self):
        return self.proxy.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.proxy.__exit__(exc_type, exc_val, exc_tb)

    def __del__(self):
        self.proxy.__del__()
