

class Bcl2FastqLogFileProvider:

    def __init__(self, config):
        self.config = config

    def log_file_path(self, runfolder):
        log_base_path = self.config["bcl2fastq_logs_path"]
        log_file = "{0}/{1}.log".format(log_base_path, runfolder)
        return log_file

    def get_log_for_runfolder(self, runfolder):
        log_path = self.log_file_path(runfolder)
        with open(log_path) as f:
            file_content = f.read()
        return file_content

