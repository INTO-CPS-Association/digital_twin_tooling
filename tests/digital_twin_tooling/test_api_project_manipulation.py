from app_base_test import BaseCase
import unittest
import yaml
import json


class TestProjectManipulation(BaseCase):

    def test_put_project(self):
        response = self.app.get('/projects')
        self.assertEqual(200, response.status_code)
        self.assertEqual(None, response.json)

        response = self.app.post('/projects/p1')
        self.assertEqual(200, response.status_code)

        response = self.app.put('/projects/p1')
        self.assertEqual(405, response.status_code)

    def test_put_del_project(self):
        response = self.app.get('/projects')
        self.assertEqual(200, response.status_code)
        self.assertEqual(None, response.json)

        response = self.app.post('/projects/p1')
        self.assertEqual(200, response.status_code)

        response = self.app.delete('/projects/p1')
        self.assertEqual(200, response.status_code)

        response = self.app.get('/projects')
        self.assertEqual(200, response.status_code)
        self.assertEqual(None, response.json)

    def test_post_project(self):
        response = self.app.get('/projects')
        self.assertEqual(200, response.status_code)
        self.assertEqual(None, response.json)

        project_json = yaml.safe_load('''
version: '0.0.2'
tools:
  google:
    path: "tools/img.png"
    url: https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png
        ''')

        response = self.app.post('/projects/p1', headers={"Content-Type": "application/json"},
                                 data=json.dumps(project_json))
        self.assertEqual(200, response.status_code)

        response = self.app.get('/projects/p1')
        self.assertEqual(200, response.status_code)
        self.assertEqual(project_json, response.json)

        project_json = yaml.safe_load('''
version: '0.0.2'
tools:
  google2:
    path: "tools/img.png"
    url: https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png
  google:
    path: "tools/img.png"
    url: https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png
        ''')

        response = self.app.post('/projects/p1', headers={"Content-Type": "application/json"},
                                 data=json.dumps(project_json))
        self.assertEqual(405, response.status_code)

        response = self.app.put('/projects/p1/config', headers={"Content-Type": "application/json"},
                                data=json.dumps(project_json))
        self.assertEqual(200, response.status_code)

        response = self.app.get('/projects/p1')
        self.assertEqual(200, response.status_code)
        self.assertEqual(project_json, response.json)

    def test_post_sub_element_server(self):
        response = self.app.post('/projects/p1', headers={"Content-Type": "application/json"},
                                 data=json.dumps({}))
        self.assertEqual(200, response.status_code)

        server_json = yaml.safe_load('''
      server_98:
        name: Implicit embedded SQLite datastore
        type: MQLite
        embedded: true''')

        response = self.app.post('/projects/p1/config/servers', headers={"Content-Type": "application/json"},
                                 data=json.dumps(server_json))
        self.assertEqual(200, response.status_code)

        response = self.app.get('/projects/p1/config/servers')
        self.assertEqual(200, response.status_code)
        self.assertEqual(server_json, response.json)

        response = self.app.delete('/projects/p1/config/servers/server_98')
        self.assertEqual(200, response.status_code)

        response = self.app.get('/projects/p1/config/servers')
        self.assertEqual(200, response.status_code)
        self.assertEqual({}, response.json)

    def test_post_sub_element_tools(self):
        response = self.app.post('/projects/p1', headers={"Content-Type": "application/json"},
                                 data=json.dumps({}))
        self.assertEqual(200, response.status_code)

        server_json = yaml.safe_load('''
      my_tool:
        name: Some random toop
        type: MaestroV2
        path: tools/something.jar''')

        response = self.app.post('/projects/p1/config/tools', headers={"Content-Type": "application/json"},
                                 data=json.dumps(server_json))
        self.assertEqual(200, response.status_code)

        response = self.app.get('/projects/p1/config/tools')
        self.assertEqual(200, response.status_code)
        self.assertEqual(server_json, response.json)

        response = self.app.delete('/projects/p1/config/tools/my_tool')
        self.assertEqual(200, response.status_code)

        response = self.app.get('/projects/p1/config/tools')
        self.assertEqual(200, response.status_code)
        self.assertEqual({}, response.json)

    def test_post_sub_element_configuration_no_tasks(self):
        response = self.app.post('/projects/p1', headers={"Content-Type": "application/json"},
                                 data=json.dumps({}))
        self.assertEqual(200, response.status_code)

        config_json = yaml.safe_load('''
      name: my config''')

        response = self.app.post('/projects/p1/config/configurations', headers={"Content-Type": "application/json"},
                                 data=json.dumps(config_json))
        self.assertEqual(200, response.status_code)
        self.assertTrue('id' in response.json)

        id = response.json['id']

        response = self.app.get('/projects/p1/config/configurations/' + id)
        self.assertEqual(200, response.status_code)
        tmp = response.json
        del tmp['id']
        self.assertEqual(config_json, tmp)

        return response.json

    def test_post_sub_element_configuration_tasks_empty(self):
        response = self.app.post('/projects/p1', headers={"Content-Type": "application/json"},
                                 data=json.dumps({}))
        self.assertEqual(200, response.status_code)

        config_json = {"name":"my name","tasks":[]}

        response = self.app.post('/projects/p1/config/configurations', headers={"Content-Type": "application/json"},
                                 data=json.dumps(config_json))
        self.assertEqual(200, response.status_code)
        self.assertTrue('id' in response.json)

        id = response.json['id']

        response = self.app.get('/projects/p1/config/configurations/' + id)
        self.assertEqual(200, response.status_code)
        tmp = response.json
        del tmp['id']
        self.assertEqual(config_json, tmp)

    def test_post_sub_element_configuration_one_task(self):
        response = self.app.post('/projects/p1', headers={"Content-Type": "application/json"},
                                 data=json.dumps({}))
        self.assertEqual(200, response.status_code)

        task_json = yaml.safe_load('''
               amqp-repeater:
                  name: jjj
        #          execution:
        #            tool: AMQP-AMQP
                  prepare:
                    tool: rabbitmq
        #          implementation: python
                  servers:
                    source: server_1
                    target: server_1
                  signals:
                    level:
                      source:
                        exchange: level_exchange
                        datatype: double
                      target:
                        exchange: wt
                        pack: JSON
                        path: level
                        datatype: double
                    valve:
                      source:
                        exchange: valve_exchange
                        datatype: double
                      target:
                        exchange: wt
                        pack: JSON
                        path: valve
                        datatype: double''')

        config_json = {"name":"my name","tasks":[task_json]}

        response = self.app.post('/projects/p1/config/configurations', headers={"Content-Type": "application/json"},
                                 data=json.dumps(config_json))
        self.assertEqual(200, response.status_code)
        self.assertTrue('id' in response.json)
        self.assertTrue('id' in response.json['tasks'][0])

        id = response.json['id']

        response = self.app.get('/projects/p1/config/configurations/' + id)
        self.assertEqual(200, response.status_code)
        tmp = response.json
        del tmp['id']
        del tmp['tasks'][0]['id']
        self.assertEqual(config_json, tmp)

    def test_post_sub_element_configuration(self):
        id =self.test_post_sub_element_configuration_no_tasks()['id']

        config2_json = yaml.safe_load('''
        name: my config 2''')

        response = self.app.put('/projects/p1/config/configurations/' + id,
                                headers={"Content-Type": "application/json"},
                                data=json.dumps(config2_json))
        self.assertEqual(200, response.status_code)
        self.assertTrue('id' in response.json)
        self.assertEqual('my config 2', response.json['name'])

        response = self.app.delete('/projects/p1/config/configurations/' + id)
        self.assertEqual(200, response.status_code)

        response = self.app.get('/projects/p1/config/configurations')
        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json)

    def test_post_sub_element_configuration_task(self):
        response = self.app.post('/projects/p1', headers={"Content-Type": "application/json"},
                                 data=json.dumps({}))
        self.assertEqual(200, response.status_code)

        config_json = yaml.safe_load('''
      name: my config''')

        response = self.app.post('/projects/p1/config/configurations', headers={"Content-Type": "application/json"},
                                 data=json.dumps(config_json))
        self.assertEqual(200, response.status_code)
        self.assertTrue('id' in response.json)

        config_id = response.json['id']

        task_json = yaml.safe_load('''
       amqp-repeater:
          name: jjj
#          execution:
#            tool: AMQP-AMQP
          prepare:
            tool: rabbitmq
#          implementation: python
          servers:
            source: server_1
            target: server_1
          signals:
            level:
              source:
                exchange: level_exchange
                datatype: double
              target:
                exchange: wt
                pack: JSON
                path: level
                datatype: double
            valve:
              source:
                exchange: valve_exchange
                datatype: double
              target:
                exchange: wt
                pack: JSON
                path: valve
                datatype: double''')

        response = self.app.post('/projects/p1/config/configurations/' + config_id + '/tasks',
                                 headers={"Content-Type": "application/json"},
                                 data=json.dumps(task_json))
        self.assertEqual(200, response.status_code)
        self.assertTrue('id' in response.json)

        task_id = response.json['id']

        response = self.app.get('/projects/p1/config/configurations/' + config_id+'/tasks/'+task_id)
        self.assertEqual(200, response.status_code)
        tmp = response.json
        del tmp['id']
        self.assertEqual(task_json, tmp)

        task_json2 = yaml.safe_load('''
               amqp-repeater:
                  name: Something else
        #          execution:
        #            tool: AMQP-AMQP
                  prepare:
                    tool: rabbitmq
        #          implementation: python
                  servers:
                    source: server_1
                    target: server_1
                  signals:
                    level:
                      source:
                        exchange: level_exchange
                        datatype: double
                      target:
                        exchange: wt
                        pack: JSON
                        path: level
                        datatype: double
                    valve:
                      source:
                        exchange: valve_exchange
                        datatype: double
                      target:
                        exchange: wt
                        pack: JSON
                        path: valve
                        datatype: double''')

        response = self.app.put('/projects/p1/config/configurations/' + config_id+'/tasks/'+task_id,
                                headers={"Content-Type": "application/json"},
                                data=json.dumps(task_json2))
        self.assertEqual(200, response.status_code)
        self.assertTrue('id' in response.json)
        self.assertEqual('Something else', response.json['amqp-repeater']['name'])

        response = self.app.delete('/projects/p1/config/configurations/' + config_id+'/tasks/'+task_id)
        self.assertEqual(200, response.status_code)

        response = self.app.get('/projects/p1/config/configurations/'+ config_id+'/tasks')
        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json)


if __name__ == '__main__':
    unittest.main()
