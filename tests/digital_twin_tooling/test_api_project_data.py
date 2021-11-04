from app_base_test import BaseCase
import unittest


class TestProjectData(BaseCase):

    def test_project_schema(self):
        response = self.app.get('/project/schemas')
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.json))


if __name__ == '__main__':
    unittest.main()
