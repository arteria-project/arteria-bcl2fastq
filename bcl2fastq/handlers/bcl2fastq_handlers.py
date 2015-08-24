
from bcl2fastq.handlers.base_handler import BaseHandler
from bcl2fastq.lib.jobrunner import LocalQAdapter
from bcl2fastq.lib.bcl2fastq_utils import BCL2FastqRunnerFactory, Bcl2FastqConfig
from bcl2fastq.lib.config import Config

import json
import logging

from bcl2fastq.handlers.base_handler import BaseHandler
from bcl2fastq.lib.jobrunner import LocalQAdapter
from bcl2fastq.lib.bcl2fastq_utils import BCL2FastqRunnerFactory, Bcl2FastqConfig
from bcl2fastq.lib.config import Config
from arteria.web.state import State

log = logging.getLogger(__name__)

class Bcl2FastqServiceMixin:
    """
    Provides bcl2fastq related services that can be mixed in.
    It will create adaptors to the runner service the first time a
    request is made and then keep that adaptor. These adaptors are static,
    so that only one such adaptor is created for the entire application.
    """

    _runner_service = None

    @staticmethod
    def runner_service():
        """
        Create an adaptor to the runner service unless one already exists
        """
        if Bcl2FastqServiceMixin._runner_service:
            return Bcl2FastqServiceMixin._runner_service
        else:
            import multiprocessing
            nbr_of_cores = multiprocessing.cpu_count()
            # TODO Make configurable
            Bcl2FastqServiceMixin._runner_service = LocalQAdapter(nbr_of_cores=nbr_of_cores, interval=2)
            return Bcl2FastqServiceMixin._runner_service

    _bcl2fastq_cmd_generation_service = None

    @staticmethod
    def bcl2fastq_cmd_generation_service():
        """
        Create a command generation service unless one already exists.
        """
        if Bcl2FastqServiceMixin._bcl2fastq_cmd_generation_service:
            return Bcl2FastqServiceMixin._bcl2fastq_cmd_generation_service
        else:
            Bcl2FastqServiceMixin._bcl2fastq_cmd_generation_service = BCL2FastqRunnerFactory()
            return Bcl2FastqServiceMixin._bcl2fastq_cmd_generation_service


class VersionsHandler(BaseHandler):
    """
    Get the available bcl2fastq versions that the
    service knows about.
    """
    def get(self):
        config = Config.load_config()
        available_versions = config["bcl2fastq"]["versions"].keys()
        self.write_object(available_versions)

class StartHandler(BaseHandler, Bcl2FastqServiceMixin):
    """
    Start bcl2fastq
    """

    def create_config_from_request(self, runfolder, request_data):
        """
        For the specified runfolder, will look it up from the place setup in the
        configuration, and then parse additinoal data from the request_data object.
        This can be used to override any default setting in the resulting Bcl2FastqConfig
        instance.
        :param runfolder: name of the runfolder we want to create a config for
        :param request_data: dict containing additional configurations
        :return: an instances of Bcl2FastqConfig
        """

        # TODO Make sure to escape them for sec. reasons.
        bcl2fastq_version = ""
        runfolder_input = ""
        output = ""
        barcode_mismatches = ""
        tiles = ""
        use_base_mask = ""
        additional_args = ""

        runfolder_base_path = Config.load_config()["runfolder_path"]
        runfolder_input = "{0}/{1}".format(runfolder_base_path, runfolder)

        import os.path as p
        if not p.isdir(runfolder_input):
            raise RuntimeError("No such file: {0}".format(runfolder_input))

        if "bcl2fastq_version" in request_data:
            bcl2fastq_version = request_data["bcl2fastq_version"]

        if "output" in request_data:
            output = request_data["output"]

        if "barcode_mismatches" in request_data:
            barcode_mismatches = request_data["barcode_mismatches"]

        if "tiles" in request_data:
            tiles = request_data["tiles"]

        if "use_base_mask" in request_data:
            use_base_mask = request_data["use_base_mask"]

        if "additional_args" in request_data:
            additional_args = request_data["additional_args"]

        config = Bcl2FastqConfig(
            bcl2fastq_version,
            runfolder_input,
            output,
            barcode_mismatches,
            tiles,
            use_base_mask,
            additional_args)

        return config

    def post(self, runfolder):
        """
        Starts a bcl2fastq for a runfolder. The input data can contain extra
        parameters for bcl2fastq. It should be a json encoded object and
        can contain one or more of the following parameters:
         - bcl2fastq_version
         - output
         - barcode_mismatches
         - tiles
         - use_base_mask
         - additional_args
        If these are not set defaults setup in Bcl2FastqConfig will be
        used (and those should be good enough for most cases).

        :param runfolder: name of the runfolder we want to start bcl2fastq for
        """

        try:
            #TODO Make sure this works even if body is not set! /JD 20150820
            runfolder_config = self.create_config_from_request(runfolder, json.loads(self.request.body))

            cmd = self.bcl2fastq_cmd_generation_service().\
                create_bcl2fastq_runner(runfolder_config).\
                construct_command()

            general_config = Config.load_config()
            log_base_path = general_config["bcl2fastq_logs_path"]
            log_file = "{0}/{1}.log".format(log_base_path, runfolder)

            job_id = self.runner_service().start(
                cmd,
                nbr_of_cores=runfolder_config.nbr_of_cores,
                run_dir=runfolder_config.runfolder_input,
                stdout=log_file,
                stderr=log_file)

            status_end_point = "{0}://{1}{2}".format(
                self.request.protocol,
                self.request.host,
                self.reverse_url("status", job_id))

            response_data = {"job_id": job_id, "link": status_end_point, "state": State.STARTED}

            self.set_status(202, reason="started processing")
            self.write_json(response_data)
        except RuntimeError as e:
            self.send_error(status_code=500, reason=e.message)


class StatusHandler(BaseHandler, Bcl2FastqServiceMixin):
    """
    Get the status of one or all jobs.
    """

    def get(self, job_id):
        """
        Get the status of the specified job_id, or if now id is given, the
        status of all jobs.
        :param job_id: to check status for (set to empty to get status for all)
        """

        if job_id:
            status = {"state": self.runner_service().status(job_id)}
        else:
            all_status = self.runner_service().status_all()
            status_dict = {}
            for k,v in all_status.iteritems():
                status_dict[k] = {"state": v}
            status = status_dict

        self.write_json(status)


class StopHandler(BaseHandler, Bcl2FastqServiceMixin):
    """
    Stop one or all jobs.
    """

    def post(self, job_id):
        """
        Stops the job with the specified id.
        :param job_id: of job to stop, or set to "all" to stop all jobs
        """
        try:
            if job_id == "all":
                self.runner_service().stop_all()
                self.set_status(200)
            elif job_id:
                self.runner_service().stop(job_id)
                self.set_status(200)
            else:
                ValueError("Unknown job to stop")
        except ValueError as e:
            self.send_error(500, reason=e.message)



