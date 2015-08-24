
import unittest
from bcl2fastq.lib.jobrunner import LocalQAdapter
from arteria.web.state import State
import time

class TestLocalQAdapter(unittest.TestCase):

    server_adapter = None

    echo = "ls -l"
    sleep = "sleep 2"

    def setUp(self):
        self.server_adapter = LocalQAdapter(nbr_of_cores=1, interval=1)

    def tearDown(self):
        self.server_adapter = None

    def test_start(self):
        result = self.server_adapter.start(self.echo, 1, "/tmp")
        self.assertEqual(result, 1)

    def test_stop(self):
        job_id = self.server_adapter.start(self.sleep, 1, "/tmp")
        result = self.server_adapter.stop(job_id)
        self.assertEqual(result, job_id)

    def test_stop_non_existent(self):
        result = self.server_adapter.stop(123)
        self.assertEqual(result, None)

    def test_stop_all(self):
        self.server_adapter.stop_all()
        result = self.server_adapter.status_all()
        self.assertEqual(result, {})

    def test_status(self):
        job_id = self.server_adapter.start(self.echo, 1, "/tmp")
        time.sleep(2)
        result = self.server_adapter.status(job_id)
        self.assertEqual(result, State.DONE)

    def test_status_all(self):
        job_id_1 = self.server_adapter.start(self.echo, 1, "/tmp")
        job_id_2 = self.server_adapter.start(self.echo, 1, "/tmp")
        result = self.server_adapter.status_all()
        self.assertEqual(result, {job_id_1: State.PENDING, job_id_2: State.PENDING})


