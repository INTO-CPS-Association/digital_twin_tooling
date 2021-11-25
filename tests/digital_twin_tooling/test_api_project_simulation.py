import time
import urllib.parse

from app_base_test import BaseCase
import unittest
import yaml
from pathlib import Path
import json
from digital_twin_tooling.app import  app
from tests.digital_twin_tooling.testcontainer_python_rabbitmq_ci import RabbitMQContainerCI


class TestProjectSimulationData(BaseCase):

    def test_project_simulation(self):
        with open(Path(__file__).parent / 'basic2.yml') as f:
            project_data = yaml.load(f, Loader=yaml.FullLoader)

            response = self.app.post('/projects/my_execution_project', headers={"Content-Type": "application/json"},
                                     data=json.dumps(project_data))
            self.assertEqual(200, response.status_code)

            response = self.app.get('/projects/my_execution_project/config/configurations')
            self.assertEqual(200, response.status_code)

            configs = response.json

            simulation_conf_id = None
            for s in configs:
                for t in s['tasks']:
                    if 'simulation' in t:
                        simulation_conf_id = s['id']

            # lets prepare the data repeater
            data_repeater_id = None
            sim_id = None
            for t in s['tasks']:
                if 'simulation' in t:
                    sim_id = t['id']
                elif 'amqp-repeater' in t:
                    data_repeater_id = t['id']

            # generate the rabbitmq fmu
            response = self.app.post(
                '/projects/my_execution_project/prepare/config/configurations/{}/tasks/{}'.format(simulation_conf_id,
                                                                                                  data_repeater_id))
            self.assertEqual(200, response.status_code)
            self.assertTrue('file' in response.json)

            repeater_fmu_path = response.json['file']

            # update the simulation with the new version of the fmu
            response = self.app.put(
                '/projects/my_execution_project/config/configurations/' + simulation_conf_id + '/tasks/' + sim_id + '/simulation/config/fmus/{amqp}',
                headers={"Content-Type": "application/json"},
                data=json.dumps(repeater_fmu_path))
            self.assertEqual(200, response.status_code)

            # prepare the specification
            # response = self.app.post(
            #     '/projects/my_execution_project/prepare/config/configurations/' + simulation_conf_id + '/tasks/' + sim_id)
            # self.assertEqual(200, response.status_code)

            config = RabbitMQContainerCI(image="rabbitmq:3.9.5-management")
            with config as container:
                print(container.get_url())

                response = self.app.post('/projects/my_execution_project/config/servers/server_1',
                                         headers={"Content-Type": "application/json"},
                                         data=json.dumps({
                                             'name': 'Remote AMQP System 1',
                                             'user': 'guest',
                                             'password': 'guest',
                                             'host': container.get_container_host_ip(),
                                             'port': int(container.get_amqp_port()),
                                             'type': 'AMQP',
                                             'embedded': True
                                         }))
                self.assertEqual(200, response.status_code)

                # fmu paths
                fmu_search_path = ",".join([app.config["PROJECT_BASE"], str(Path(__file__).parent / 'fmus')])

                response = self.app.post(
                    '/projects/my_execution_project/execution/configurations/{}/run?{}'.format(simulation_conf_id,
                                                                                              urllib.parse.urlencode({
                                                                                                                         'fmus': fmu_search_path})))
                self.assertEqual(200, response.status_code)

                response = self.app.get(
                    '/projects/my_execution_project/execution/configurations/{}/status'.format(simulation_conf_id))
                self.assertEqual(200, response.status_code)
                print(response.json)


if __name__ == '__main__':
    unittest.main()
