
import json
import logging
import os

from bcl2fastq.lib.jobrunner import LocalQAdapter
from bcl2fastq.lib.bcl2fastq_utils import BCL2FastqRunnerFactory, Bcl2FastqConfig
from bcl2fastq import __version__ as version
from bcl2fastq.lib.bcl2fastq_logs import Bcl2FastqLogFileProvider
from arteria.exceptions import ArteriaUsageException
from arteria.web.state import State
from arteria.web.handlers import BaseRestHandler


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
    def bcl2fastq_cmd_generation_service(config):
        """
        Create a command generation service unless one already exists.
        """
        if Bcl2FastqServiceMixin._bcl2fastq_cmd_generation_service:
            return Bcl2FastqServiceMixin._bcl2fastq_cmd_generation_service
        else:
            Bcl2FastqServiceMixin._bcl2fastq_cmd_generation_service = BCL2FastqRunnerFactory(config)
            return Bcl2FastqServiceMixin._bcl2fastq_cmd_generation_service

class BaseBcl2FastqHandler(BaseRestHandler):
    """
    Base handler for bcl2fastq.
    """

    def initialize(self, config):
        """
        Ensures that any parameters feed to this are available
        to subclasses.
        """
        self.config = config
        self.bcl2fastq_log_file_provider = Bcl2FastqLogFileProvider(self.config)


class VersionsHandler(BaseBcl2FastqHandler):
    """
    Get the available bcl2fastq versions that the
    service knows about.
    """

    def get(self):
        """
        Returns all available bcl2fastq versions (as defined by config).
        """
        available_versions = self.config["bcl2fastq"]["versions"]
        self.write_object(available_versions)

class StartHandler(BaseBcl2FastqHandler, Bcl2FastqServiceMixin):
    """
    Start bcl2fastq
    """

    def create_config_from_request(self, runfolder, request_body):
        """
        For the specified runfolder, will look it up from the place setup in the
        configuration, and then parse additional data from the request_data object.
        This can be used to override any default setting in the resulting Bcl2FastqConfig
        instance.
        :param runfolder: name of the runfolder we want to create a config for
        :param request_body: the body of the request. Can be empty, in which case if will not be loaded.
        :return: an instances of Bcl2FastqConfig
        """

        if request_body:
            request_data = json.loads(request_body)
        else:
            request_data = {}

        # TODO Make sure to escape them for sec. reasons.
        bcl2fastq_version = ""
        runfolder_input = ""
        samplesheet = ""
        output = ""
        barcode_mismatches = ""
        tiles = ""
        use_base_mask = ""
        create_indexes = False
        additional_args = ""

        runfolder_base_path = self.config["runfolder_path"]
        runfolder_input = "{0}/{1}".format(runfolder_base_path, runfolder)

        if not os.path.isdir(runfolder_input):
            raise ArteriaUsageException("No such file: {0}".format(runfolder_input))

        if "bcl2fastq_version" in request_data:
            bcl2fastq_version = request_data["bcl2fastq_version"]

        if "output" in request_data:
            output = request_data["output"]

        if "samplesheet" in request_data:
            samplesheet = request_data["samplesheet"]

        if "barcode_mismatches" in request_data:
            barcode_mismatches = request_data["barcode_mismatches"]

        if "tiles" in request_data:
            tiles = request_data["tiles"]

        if "use_base_mask" in request_data:
            use_base_mask = request_data["use_base_mask"]

        if "create_indexes" in request_data:
            if request_data["create_indexes"] == "True":
                create_indexes = True

        if "additional_args" in request_data:
            additional_args = request_data["additional_args"]

        config = Bcl2FastqConfig(
            self.config,
            bcl2fastq_version,
            runfolder_input,
            output,
            samplesheet,
            barcode_mismatches,
            tiles,
            use_base_mask,
            create_indexes,
            additional_args)

        return config

    def post(self, runfolder):
        """
        Starts a bcl2fastq for a runfolder. The input data can contain extra
        parameters for bcl2fastq. It should be a json encoded object and
        can contain one or more of the following parameters:
         - bcl2fastq_version
         - output
         - samplesheet (provide the entire samplesheet in the request)
         - barcode_mismatches
         - tiles
         - use_base_mask
         - additional_args
        If these are not set defaults setup in Bcl2FastqConfig will be
        used (and those should be good enough for most cases).

        :param runfolder: name of the runfolder we want to start bcl2fastq for
        """

        try:
            runfolder_config = self.create_config_from_request(runfolder, self.request.body)

            job_runner = self.bcl2fastq_cmd_generation_service(self.config). \
                create_bcl2fastq_runner(runfolder_config)
            bcl2fastq_version = job_runner.version()
            cmd = job_runner.construct_command()
            # If the output directory exists, we always want to clear it.
            job_runner.delete_output()
            job_runner.symlink_output_to_unaligned()

            log_file = self.bcl2fastq_log_file_provider.log_file_path(runfolder)

            job_id = self.runner_service().start(
                cmd,
                nbr_of_cores=runfolder_config.nbr_of_cores,
                run_dir=runfolder_config.runfolder_input,
                stdout=log_file,
                stderr=log_file)

            log.info(
                "Cmd: {} started in {} with {} cores. Writing logs to: {}".format(cmd,
                                                                                  runfolder_config.runfolder_input,
                                                                                  runfolder_config.nbr_of_cores,
                                                                                  log_file))

            status_end_point = "{0}://{1}{2}".format(
                self.request.protocol,
                self.request.host,
                self.reverse_url("status", job_id))

            response_data = {
                "job_id": job_id,
                "bcl2fastq_version": bcl2fastq_version,
                "service_version": version,
                "link": status_end_point,
                "state": State.STARTED}

            self.set_status(202, reason="started processing")
            self.write_json(response_data)
        except ArteriaUsageException as e:
            log.warning("Failed starting {0}. Message: {1}".format(runfolder, e.message))
            self.send_error(status_code=500, reason=e.message)



class StatusHandler(BaseBcl2FastqHandler, Bcl2FastqServiceMixin):
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


class StopHandler(BaseBcl2FastqHandler, Bcl2FastqServiceMixin):
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
                log.info("Attempting to stop all jobs.")
                self.runner_service().stop_all()
                log.info("Stopped all jobs!")
                self.set_status(200)
            elif job_id:
                log.info("Attempting to stop job: {}".format(job_id))
                self.runner_service().stop(job_id)
                self.set_status(200)
            else:
                ArteriaUsageException("Unknown job to stop")
        except ArteriaUsageException as e:
            log.warning("Failed stopping job: {}. Message: ".format(job_id, e.message))
            self.send_error(500, reason=e.message)


class Bcl2FastqLogHandler(BaseBcl2FastqHandler):
    """
    Gets the content of the log for a particular runfolder
    """

    def get(self, runfolder):
        """
        Get the content of the log for a particular runfolder
        :param runfolder:
        :return:
        """
        try:
            log_content = self.bcl2fastq_log_file_provider.get_log_for_runfolder(runfolder)
            response_data = {"runfolder": runfolder, "log": log_content}
            self.set_status(200)
            self.write_json(response_data)
        except IOError as e:
            log.warning("Problem with accessing {}, message: {}".format(runfolder, e.message))
            self.send_error(500, reason=e.message)
