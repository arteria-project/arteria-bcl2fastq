
from bcl2fastq.handlers.base_handler import BaseHandler

class ApiHelpEntry:
    """
    Simple container used to create a API help entry.
    """

    @staticmethod
    def prefix():
        """
        Set this function to what ever you want to prefix the api help entries with.
        """
        raise NotImplementedError("Needs to be set, e.g. 'ApiHelpEntry.prefix = self.api_link()'")

    def __init__(self, link, description):
        self.link = self.prefix + link
        self.description = description

class ApiHelpHandler(BaseHandler):
    """
    Provides the base for the api help. Use it to list end-points and give
    hints on how to use them.
    """

    def get(self):
        ApiHelpEntry.prefix = self.api_link()
        doc = [
            ApiHelpEntry("/versions", "Lists available version of bcl2fastq"),
            ApiHelpEntry("/start/<runfolder>", "Starts a the specified runfolder. Specify arguments in body."
                                               "Will return job_id and endpoint to query for status."),
            ApiHelpEntry("/stop/<job_id | all>", "Stop the job with id <job_id>, or all jobs if 'all' is specified."),
            ApiHelpEntry("/status/<optional: job_id>", "If no job_id is specified, it will return the status"
                                                       "of all jobs, otherwise the status of the job with id: job_id"),
        ]
        self.write_object(doc)