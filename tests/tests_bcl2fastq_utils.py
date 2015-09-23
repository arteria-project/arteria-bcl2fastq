import unittest
from mock import patch
import tempfile
import os

from bcl2fastq.lib.bcl2fastq_utils import *
from bcl2fastq.lib.illumina import Samplesheet
from test_utils import TestUtils, DummyConfig


DUMMY_CONFIG = DummyConfig()

class TestBcl2FastqConfig(unittest.TestCase):

    test_dir = os.path.dirname(os.path.realpath(__file__))
    samplesheet_file = test_dir + "/sampledata/new_samplesheet_example.csv"

    def test_get_bcl2fastq_version_from_run_parameters(self):
        runfolder = TestBcl2FastqConfig.test_dir + "/sampledata/HiSeq-samples/2014-02_13_average_run"
        version = Bcl2FastqConfig.get_bcl2fastq_version_from_run_parameters(runfolder, TestUtils.DUMMY_CONFIG)
        self.assertEqual(version, "1.8.4")

    def test_get_length_of_indexes(self):
        runfolder = TestBcl2FastqConfig.test_dir + "/sampledata/HiSeq-samples/2014-02_13_average_run"
        index_and_length = Bcl2FastqConfig.get_length_of_indexes(runfolder)
        self.assertEqual(index_and_length, {2: 7})

    def test_write_samplesheet(self):
        f = tempfile.mktemp()
        Bcl2FastqConfig.write_samplesheet(TestUtils.DUMMY_SAMPLESHEET_STRING, f)
        with open(f, "r") as my_file:
            content = my_file.read()
            self.assertEqual(content, TestUtils.DUMMY_SAMPLESHEET_STRING)
        os.remove(f)

    def test_samplesheet_gets_written(self):
        with patch.object(Bcl2FastqConfig, "write_samplesheet") as ws:
            # If we provide a samplesheet to the config this should be written.
            # In this case this write call is mocked away to make testing easier,
            # but the write it self should be trivial.
            config = Bcl2FastqConfig(
                general_config = DUMMY_CONFIG,
                bcl2fastq_version = "1.8.4",
                runfolder_input = "test/runfolder",
                output = "test/output",
                samplesheet=TestUtils.DUMMY_SAMPLESHEET_STRING)

            ws.assert_called_once_with(TestUtils.DUMMY_SAMPLESHEET_STRING, config.samplesheet_file)

    def test_get_bases_mask_per_lane_from_samplesheet(self):
        mock_read_index_lengths = {2: 9, 3: 9}
        expected_bases_mask = {1: "y*,i8n*,i8n*,y*",
                               2: "y*,i6n*,n*,y*",
                               3: "y*,i6n*,n*,y*",
                               4: "y*,i7n*,n*,y*",
                               5: "y*,i7n*,n*,y*",
                               6: "y*,i7n*,n*,y*",
                               7: "y*,i7n*,n*,y*",
                               8: "y*,i7n*,n*,y*",
                               }
        samplesheet = Samplesheet(TestBcl2FastqConfig.samplesheet_file)
        actual_bases_mask = Bcl2FastqConfig. \
            get_bases_mask_per_lane_from_samplesheet(samplesheet, mock_read_index_lengths)
        self.assertEqual(expected_bases_mask, actual_bases_mask)

    def test_get_bases_mask_per_lane_from_samplesheet_invalid_length_combo(self):
        # These are to short compared to the length indicated in the samplesheet
        mock_read_index_lengths = {2: 4, 3: 4}
        samplesheet = Samplesheet(TestBcl2FastqConfig.samplesheet_file)

        with self.assertRaises(AssertionError):
            Bcl2FastqConfig. \
                get_bases_mask_per_lane_from_samplesheet(samplesheet, mock_read_index_lengths)


class TestBCL2FastqRunnerFactory(unittest.TestCase):

    def test_create_bcl2fastq1x_runner(self):
        config = Bcl2FastqConfig(
            general_config = DUMMY_CONFIG,
            bcl2fastq_version = "1.8.4",
            runfolder_input = "test/runfolder",
            output = "test/output")

        factory = BCL2FastqRunnerFactory(TestUtils.DUMMY_CONFIG)
        runner = factory.create_bcl2fastq_runner(config)
        self.assertIsInstance(runner, BCL2Fastq1xRunner)

    def test_create_bcl2fastq2x_runner(self):
        config = Bcl2FastqConfig(
            general_config = DUMMY_CONFIG,
            bcl2fastq_version = "2.15.2",
            runfolder_input = "test/runfolder",
            output = "test/output")

        factory = BCL2FastqRunnerFactory(TestUtils.DUMMY_CONFIG)
        runner = factory.create_bcl2fastq_runner(config)
        self.assertIsInstance(runner, BCL2Fastq2xRunner, msg="runner is: " + str(runner))

    def test_create_invalid_version_runner(self):
        config = Bcl2FastqConfig(
            general_config = DUMMY_CONFIG,
            bcl2fastq_version = "1.7",
            runfolder_input = "test/runfolder",
            output = "test/output")

        factory = BCL2FastqRunnerFactory(TestUtils.DUMMY_CONFIG)
        with self.assertRaises(LookupError):
            factory.create_bcl2fastq_runner(config)


class TestBCL2Fastq2xRunner(unittest.TestCase):
    def test_construct_command(self):

        config = Bcl2FastqConfig(
            general_config = DUMMY_CONFIG,
            bcl2fastq_version = "2.15.2",
            runfolder_input = "test/runfolder",
            output = "test/output",
            barcode_mismatches = "2",
            tiles="s1,s2,s3",
            use_base_mask="--use-bases-mask y*,i6,i6,y* --use-bases-mask 1:y*,i5,i5,y*",
            additional_args="--my-best-arg 1 --my-best-arg 2")

        runner = BCL2Fastq2xRunner(config, "/bcl/binary/path")
        command = runner.construct_command()
        expected_command = "/bcl/binary/path --input-dir test/runfolder/Data/Intensities/BaseCalls " \
                           "--output-dir test/output " \
                           "--sample-sheet test/runfolder/SampleSheet.csv " \
                           "--barcode-mismatches 2 " \
                           "--tiles s1,s2,s3 " \
                           "--use-bases-mask y*,i6,i6,y* --use-bases-mask 1:y*,i5,i5,y* " \
                           "--my-best-arg 1 --my-best-arg 2"
        self.assertEqual(command, expected_command)

class TestBCL2FastqRunner(unittest.TestCase):

    config = Bcl2FastqConfig(
        general_config = DUMMY_CONFIG,
        bcl2fastq_version = "2.15.2",
        runfolder_input = "test/runfolder",
        output = "test/output",
        barcode_mismatches = "2",
        tiles="s1,s2,s3",
        use_base_mask="--use-bases-mask y*,i6,i6,y* --use-bases-mask 1:y*,i5,i5,y*",
        additional_args="--my-best-arg 1 --my-best-arg 2")

    class DummyBCL2FastqRunner(BCL2FastqRunner):
        def __init__(self, config, binary, dummy_command):
            self.dummy_command = dummy_command
            BCL2FastqRunner.__init__(self, config, binary)

        def construct_command(self):
            return self.dummy_command

    def test_symlink_output_to_unaligned(self):
        with patch.object(os, 'symlink', return_value=None) as m:
            dummy_runner = self.DummyBCL2FastqRunner(TestBCL2FastqRunner.config, None, None)
            dummy_runner.symlink_output_to_unaligned()
            m.assert_called_with(TestBCL2FastqRunner.config.output, TestBCL2FastqRunner.config.runfolder_input + "/Unaligned")

        # Check that trying to create an already existing softlink doesn't break the function.
        with patch.object(os, 'symlink', side_effect=OSError(17, "message")) as m:
            dummy_runner = self.DummyBCL2FastqRunner(TestBCL2FastqRunner.config, None, None)
            dummy_runner.symlink_output_to_unaligned()
            m.assert_called_with(TestBCL2FastqRunner.config.output, TestBCL2FastqRunner.config.runfolder_input + "/Unaligned")

        # While any other error should
        with patch.object(os, 'symlink', side_effect=OSError()) as m:
            with self.assertRaises(OSError):
                dummy_runner = self.DummyBCL2FastqRunner(TestBCL2FastqRunner.config, None, None)
                dummy_runner.symlink_output_to_unaligned()
                m.assert_called_with(TestBCL2FastqRunner.config.output, TestBCL2FastqRunner.config.runfolder_input + "/Unaligned")

    def test__successful_run(self):
        with patch.object(BCL2FastqRunner, 'symlink_output_to_unaligned', return_value=None) as m:
            dummy_runner = self.DummyBCL2FastqRunner(TestBCL2FastqRunner.config, None, "echo 'high tech low life'; exit 0")
            success = dummy_runner.run()
            self.assertTrue(success)

    def test__unsuccessful_run(self):
        with patch.object(BCL2FastqRunner, 'symlink_output_to_unaligned', return_value=None) as m:
            dummy_runner = self.DummyBCL2FastqRunner(TestBCL2FastqRunner.config, None,  "echo 'high tech low life'; exit 1")
            success = dummy_runner.run()
            self.assertFalse(success)

class TestBCL2Fastq1xRunner(unittest.TestCase):

    def test_construct_command(self):
        config = Bcl2FastqConfig(
            general_config = DUMMY_CONFIG,
            bcl2fastq_version = "1.8.4",
            runfolder_input = "test/runfolder",
            output = "test/output",
            barcode_mismatches = "2",
            tiles="s1,s2,s3",
            use_base_mask="Y*NN",
            additional_args="--my-best-arg 1 --my-best-arg 2")

        runner_1 = BCL2Fastq1xRunner(config, "/dummy/binary")
        command = runner_1.construct_command()
        expected_command = "configureBclToFastq.pl " \
                           "--input-dir test/runfolder/Data/Intensities/BaseCalls " \
                           "--sample-sheet test/runfolder/SampleSheet.csv " \
                           "--output-dir test/output " \
                           "--fastq-cluster-count 0 " \
                           "--force " \
                           "--mismatches 2 " \
                           "--tiles s1,s2,s3 " \
                           "--use_bases_mask Y*NN " \
                           "--my-best-arg 1 " \
                           "--my-best-arg 2  " \
                           "&& make -j{0}".format(config.nbr_of_cores)

        self.assertEqual(command, expected_command)
