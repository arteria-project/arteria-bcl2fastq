from localq import LocalQServer, Status
from arteria.web.state import State as arteria_state

class JobRunnerAdapter:
    """
    Specifies interface that should be used by jobrunners.
    """

    def start(self, cmd, nbr_of_cores, run_dir, stdout=None, stderr=None):
        """
        Start a job corresponding to cmd
        :param cmd: to run
        :param nbr_of_cores: cores the job needs
        :param run_dir: where to run the job
        :param stdout: Reroute stdout to here
        :param stderr: Reroute stderr to here
        :return: the jobid associated with it (None on failure).
        """
        raise NotImplementedError("Subclasses should implement this!")

    def stop(self, job_id):
        """
        Stop job with job_id
        :param job_id: of job to stop
        :return: the job_id of the stopped job, or None if not found.
        """
        raise NotImplementedError("Subclasses should implement this!")

    def stop_all(self):
        """
        Stop all jobs
        :return: Nothing
        """
        raise NotImplementedError("Subclasses should implement this!")

    def status(self, job_id):
        """
        Status of job with id
        :param job_id: to get status for.
        :return: It's status
        """
        raise NotImplementedError("Subclasses should implement this!")

    def status_all(self):
        """
        Get status for all jobs
        :param job_id: to get status for.
        :return: A dict containing all jobs with job_id as key and status as value.
        """
        raise NotImplementedError("Subclasses should implement this!")


class LocalQAdapter(JobRunnerAdapter):
    """
    An implementation of `JobRunnerAdapter` running jobs through
    localq (a jobrunner which will schedule jobs on a single node).
    """

    @staticmethod
    def localq2arteria_status(status):

        if status == Status.COMPLETED:
            return arteria_state.DONE
        elif status == Status.FAILED:
            return arteria_state.ERROR
        elif status == Status.PENDING:
            return arteria_state.PENDING
        elif status == Status.RUNNING:
            return arteria_state.STARTED
        elif status == Status.CANCELLED:
            return arteria_state.CANCELLED
        elif status == Status.NOT_FOUND:
            return arteria_state.NONE
        else:
            return arteria_state.NONE

    # TODO Make configurable
    def __init__(self, nbr_of_cores, interval = 30, priority_method = "fifo"):
        self.nbr_of_cores = nbr_of_cores
        self.server = LocalQServer(nbr_of_cores, interval, priority_method)
        self.server.run()

    def start(self, cmd, nbr_of_cores, run_dir, stdout=None, stderr=None):
        return self.server.add(cmd, nbr_of_cores, run_dir, stdout=stdout, stderr=stderr)

    def stop(self, job_id):
        return self.server.stop_job_with_id(job_id)

    def stop_all(self):
        return self.server.stop_all_jobs()

    def status(self, job_id):
        return LocalQAdapter.localq2arteria_status(self.server.get_status(job_id))

    def status_all(self):
        jobs_and_status = {}
        for k, v in self.server.get_status_all().iteritems():
            jobs_and_status[k] = LocalQAdapter.localq2arteria_status(v)
        return jobs_and_status
