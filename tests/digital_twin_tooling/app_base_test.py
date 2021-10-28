import unittest

from digital_twin_tooling.app import app
import shutil
from pathlib import Path


class BaseCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        project_base = Path('test_project_base').absolute()
        if project_base.exists():
            shutil.rmtree(str(project_base))
        self.app.application.config["PROJECT_BASE"] = str(project_base)

    # def tearDown(self):
    #     # Delete Database collections after the test is complete
    #     for collection in self.db.list_collection_names():
    #         self.db.drop_collection(collection)
