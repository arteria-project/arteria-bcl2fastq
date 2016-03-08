
import unittest
from mock import MagicMock, patch, mock_open

from bcl2fastq.lib.bcl2fastq_logs import Bcl2FastqLogFileProvider

class TestBcl2FastqLogFileProvider(unittest.TestCase):

    fake_file_content = """
    This is a nice multi-line
    string for
    you
    my friend
    """
    fake_path = "/fake/path"
    mock_config = MagicMock()
    mock_config.__getitem__.return_value = fake_path
    runfolder = "160218_ST-E00215_0070_BHKGLFCCXX"

    log_filer_provider = Bcl2FastqLogFileProvider(mock_config)

    def test_log_file_path(self):
        log_file = self.log_filer_provider.log_file_path(self.runfolder)
        self.assertEqual(log_file, "{}/{}.log".format(self.fake_path, self.runfolder))

    def test_get_log_for_runfolder(self):
        with patch("__builtin__.open", mock_open(read_data=self.fake_file_content), create=True):
            file_content = self.log_filer_provider.get_log_for_runfolder(self.runfolder)
            self.assertEqual(file_content, self.fake_file_content)

    def test_get_log_for_runfolder_does_not_exist(self):
        with self.assertRaises(IOError):
            self.log_filer_provider.get_log_for_runfolder(self.runfolder)


