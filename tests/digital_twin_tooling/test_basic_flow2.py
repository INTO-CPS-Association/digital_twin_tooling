import time
from testcontainer_python_rabbitmq import RabbitMQContainer
import unittest
import pika
import logging
from pathlib import Path
import yaml
from digital_twin_tooling import basic, launchers
import uuid
import os

from digital_twin_tooling import tools
class RRabbitMQContainer:
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
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


class BasicFlowTests2(unittest.TestCase):

    def test_tool_fetch(self):
        with open(Path(__file__).parent / 'basic2.yml', 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)
            basic.validate(conf, version="0.0.2")
            conf.update({'tools': {'google': {'path': str(Path('tools') / 'toolz' / 'image.png'),
                                              'url': 'https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png'}}})
            basic.validate(conf, version="0.0.2")
            basic.fetch_tools(conf)

    def test_basic_flow_validation(self):
        with open(Path(__file__).parent / 'basic2.yml', 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)
            basic.validate(conf, version="0.0.2")



    def test_basic_flow1(self):

        received_messages = []

        logging.basicConfig(level=logging.DEBUG, format='%(name)s %(levelname)s %(message)s')

        logging.getLogger('urllib3').setLevel(logging.ERROR)
        logging.getLogger('pika').setLevel(logging.ERROR)

        with open(Path(__file__).parent / 'basic2.yml', 'r') as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)

        config = RabbitMQContainer(image="rabbitmq:3.9.5-management")
        # config = RRabbitMQContainer()
        with config as container:
            print(config.get_url())
            amqp_server_config = {"server": container.get_container_host_ip(),
                                  "port": container.get_amqp_port(),
                                  "user": "guest",
                                  "password": "guest",
                                  "protocol": "amqp"}

            for server in conf["servers"]:
                if "embedded" in server.keys() and ("type" in server.keys() and server["type"] == "AMQP"):
                    server["user"] = "guest"
                    server["password"] = "guest"
                    server["host"] = container.get_container_host_ip()
                    server["port"] = int(container.get_amqp_port())

            # print(yaml.dump(conf))
            # basic.show(conf)

            job_id = str(uuid.uuid4())
            print("Starting new job with id: %s" % job_id)

            job_dir = Path(__file__).parent.resolve() / 'jobs' / job_id
            os.makedirs(job_dir, exist_ok=True)
            basic.validate(conf, version="0.0.2")
            tools.fetch_tools(conf)
            basic.prepare(conf, 1, job_id, job_dir=job_dir,
                          fmu_dir=Path(__file__).parent.resolve() / 'fmus')

            with open(job_dir / 'job.yml', 'w') as f:
                f.write(yaml.dump(conf))
            # print(yaml.dump(conf))
            basic.run(conf, 1, job_dir)

            credentials = pika.PlainCredentials("guest", "guest")
            parameters = pika.ConnectionParameters(container.get_container_host_ip(), container.get_amqp_port(), '/',
                                                   credentials)
            with pika.BlockingConnection(parameters) as connection:
                channel = connection.channel()

                for exchange in ["test", "fmi_digital_twin"]:
                    channel.exchange_declare(exchange=exchange, exchange_type='direct')

                print(job_dir.absolute())
                print("sending test data")
                time.sleep(5)
                for i in range(0, 100):
                    print('\rSending %d' % i, end='', flush=True)
                    channel.basic_publish(exchange='test', routing_key="level", body=str(i).encode('utf-8'))
                    channel.basic_publish(exchange='test', routing_key="valve", body=str(i).encode('utf-8'))
                    time.sleep(0.1)

                for i in range(0, 10):
                    time.sleep(1)
                    launchers.check_launcher_status(job_dir)
                    if not launchers.check_launcher_pid_status(job_dir / 'simulation_maestro.pid'):
                        return

                launchers.terminate_all_launcher(job_dir)
                with open(job_dir / "outputs.csv") as f:
                    self.assertEqual(100 + 2, len(f.readlines()))


if __name__ == '__main__':
    unittest.main()
