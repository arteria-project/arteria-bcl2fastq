from tornado.testing import *

from tornado.escape import json_encode
import mock
from test_utils import TestUtils, DummyConfig


from bcl2fastq.handlers.bcl2fastq_handlers import *
from bcl2fastq.lib.bcl2fastq_utils import BCL2Fastq2xRunner, BCL2FastqRunner
from bcl2fastq.app import routes
from tornado.web import Application
from test_utils import FakeRunner


class TestBcl2FastqHandlers(AsyncHTTPTestCase):

    _start_api_call = 0

    def start_api_call_nbr(self):
        TestBcl2FastqHandlers._start_api_call += 1
        return TestBcl2FastqHandlers._start_api_call

    API_BASE="/api/1.0"
    MOCK_BCL2FASTQ_DICT =  {1: "y*,8i,8i,y*",
                            2: "y*,6i,n*,y*",
                            3: "y*,6i,n*,y*",
                            4: "y*,7i,n*,y*",
                            5: "y*,7i,n*,y*",
                            6: "y*,7i,n*,y*",
                            7: "y*,7i,n*,y*",
                            8: "y*,7i,n*,y*",
                            }

    def get_app(self):
        dummy_config = DummyConfig()
        return Application(routes(config=dummy_config))

    def test_versions(self):
        response = self.fetch(self.API_BASE + "/versions")
        self.assertEqual(response.code, 200)
        self.assertEqual(sorted(json.loads(response.body)), sorted(["2.15.2", "1.8.4"]))

    def test_start_missing_runfolder_in_body(self):
        response = self.fetch(self.API_BASE + "/start/150415_D00457_0091_AC6281ANXX", method="POST", body = "")
        self.assertEqual(response.code, 500)

    def test_start(self):
        # Use mock to ensure that this will run without
        # creating the runfolder.
        with mock.patch.object(os.path, 'isdir', return_value=True), \
             mock.patch.object(Bcl2FastqConfig, 'get_bcl2fastq_version_from_run_parameters', return_value="2.15.2"), \
             mock.patch.object(BCL2FastqRunnerFactory, "create_bcl2fastq_runner", return_value=FakeRunner("2.15.2")), \
             mock.patch.object(BCL2FastqRunner, 'symlink_output_to_unaligned', return_value=None):

            body = {"runfolder_input": "/path/to/runfolder"}
            response = self.fetch(
                self.API_BASE + "/start/150415_D00457_0091_AC6281ANXX", method="POST", body=json_encode(body))

            api_call_nbr = self.start_api_call_nbr()

            self.assertEqual(response.code, 202)
            self.assertEqual(json.loads(response.body)["job_id"], api_call_nbr)
            expected_link = "http://localhost:{0}/api/1.0/status/{1}".format(self.get_http_port(), api_call_nbr)
            self.assertEqual(json.loads(response.body)["link"], expected_link)
            self.assertEqual(json.loads(response.body)["bcl2fastq_version"], "2.15.2")
            self.assertEqual(json.loads(response.body)["state"], "started")

    def test_start_with_empty_body(self):
        # Use mock to ensure that this will run without
        # creating the runfolder.
        with mock.patch.object(os.path, 'isdir', return_value=True), \
             mock.patch.object(Bcl2FastqConfig, 'get_bcl2fastq_version_from_run_parameters', return_value="2.15.2"), \
             mock.patch.object(BCL2FastqRunnerFactory, "create_bcl2fastq_runner", return_value=FakeRunner("2.15.2")), \
             mock.patch.object(BCL2FastqRunner, 'symlink_output_to_unaligned', return_value=None):

            response = self.fetch(self.API_BASE + "/start/150415_D00457_0091_AC6281ANXX", method="POST", body="")

            api_call_nbr = self.start_api_call_nbr()

            self.assertEqual(response.code, 202)
            self.assertEqual(json.loads(response.body)["job_id"], api_call_nbr)
            expected_link = "http://localhost:{0}/api/1.0/status/{1}".format(self.get_http_port(), api_call_nbr)
            self.assertEqual(json.loads(response.body)["link"], expected_link)
            self.assertEqual(json.loads(response.body)["bcl2fastq_version"], "2.15.2")
            self.assertEqual(json.loads(response.body)["state"], "started")

    def test_start_providing_samplesheet(self):
        # Use mock to ensure that this will run without
        # creating the runfolder.
        with mock.patch.object(os.path, 'isdir', return_value=True), \
             mock.patch.object(Bcl2FastqConfig, 'get_bcl2fastq_version_from_run_parameters', return_value="2.15.2"), \
             mock.patch.object(BCL2FastqRunner, 'symlink_output_to_unaligned', return_value=None), \
             mock.patch.object(Bcl2FastqConfig, "write_samplesheet") as ws , \
                mock.patch.object(BCL2FastqRunnerFactory, "create_bcl2fastq_runner", return_value=FakeRunner("2.15.2")):

            body = {"runfolder_input": "/path/to/runfolder", "samplesheet": TestUtils.DUMMY_SAMPLESHEET_STRING}

            response = self.fetch(
                self.API_BASE + "/start/150415_D00457_0091_AC6281ANXX", method="POST", body=json_encode(body))

            api_call_nbr = self.start_api_call_nbr()

            self.assertEqual(response.code, 202)
            self.assertEqual(json.loads(response.body)["job_id"], api_call_nbr)
            expected_link = "http://localhost:{0}/api/1.0/status/{1}".format(self.get_http_port(), api_call_nbr)
            self.assertEqual(json.loads(response.body)["link"], expected_link)
            self.assertEqual(json.loads(response.body)["bcl2fastq_version"], "2.15.2")
            self.assertEqual(json.loads(response.body)["state"], "started")
            ws.assert_called_once_with(TestUtils.DUMMY_SAMPLESHEET_STRING, "/data/biotank3/runfolders/150415_D00457_0091_AC6281ANXX/arteria_samplesheet.csv")

    def test_status_with_id(self):
        #TODO Add real tests here!
        response = self.fetch(self.API_BASE + "/status/1123456546", method="GET")
        self.assertEqual(response.code, 200)

    def test_status_without_id(self):
        #TODO Add real tests here!
        response = self.fetch(self.API_BASE + "/status/", method="GET")
        self.assertEqual(response.code, 200)

    def test_all_stop_handler(self):
        response = self.fetch(self.API_BASE + "/stop/all", method="POST", body = "")
        self.assertEqual(response.code, 200)

    def test_stop_handler(self):
        response = self.fetch(self.API_BASE + "/stop/3", method="POST", body = "")
        self.assertEqual(response.code, 200)

    def test_exception_stop_handler(self):
        response = self.fetch(self.API_BASE + "/stop/lll", method="POST", body = "")
        self.assertEqual(response.code, 500)
