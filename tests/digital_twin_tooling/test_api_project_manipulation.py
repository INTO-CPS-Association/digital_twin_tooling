from app_base_test import BaseCase
import unittest
import yaml
import json


class TestProjectManipulation(BaseCase):

    def test_put_project(self):
        response = self.app.get('/project')
        self.assertEqual(200, response.status_code)
        self.assertEqual(None, response.json)

        response = self.app.put('/project/p1')
        self.assertEqual(200, response.status_code)

        response = self.app.put('/project/p1')
        self.assertEqual(405, response.status_code)

    def test_put_del_project(self):
        response = self.app.get('/project')
        self.assertEqual(200, response.status_code)
        self.assertEqual(None, response.json)

        response = self.app.put('/project/p1')
        self.assertEqual(200, response.status_code)

        response = self.app.delete('/project/p1')
        self.assertEqual(200, response.status_code)

        response = self.app.get('/project')
        self.assertEqual(200, response.status_code)
        self.assertEqual(None, response.json)

    def test_post_project(self):
        response = self.app.get('/project')
        self.assertEqual(200, response.status_code)
        self.assertEqual(None, response.json)

        project_json = yaml.safe_load('''
version: '0.0.2'
tools:
  google:
    path: "tools/img.png"
    url: https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png
        ''')

        response = self.app.post('/project/p1', headers={"Content-Type": "application/json"},
                                 data=json.dumps(project_json))
        self.assertEqual(200, response.status_code)

        response = self.app.get('/project/p1')
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

        response = self.app.post('/project/p1', headers={"Content-Type": "application/json"},
                                 data=json.dumps(project_json))
        self.assertEqual(405, response.status_code)

        response = self.app.post('/project/p1/config', headers={"Content-Type": "application/json"},
                                 data=json.dumps(project_json))
        self.assertEqual(200, response.status_code)

        response = self.app.get('/project/p1')
        self.assertEqual(200, response.status_code)
        self.assertEqual(project_json, response.json)


if __name__ == '__main__':
    unittest.main()
