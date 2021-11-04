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


if __name__ == '__main__':
    unittest.main()
