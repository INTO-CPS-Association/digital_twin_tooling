from app_base_test import BaseCase
import unittest


class TestProjectData(BaseCase):

    def test_project_schema(self):
        response = self.app.get('/project/schema')
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.is_json)
        self.assertEqual(5, len(response.json))


if __name__ == '__main__':
    unittest.main()
