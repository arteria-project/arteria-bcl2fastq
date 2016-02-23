
from arteria.web.app import AppService
from bcl2fastq.handlers.bcl2fastq_handlers import *
from tornado.web import URLSpec as url


def routes(**kwargs):
    """
    Setup routes and feed them any kwargs passed, e.g.`routes(config=app_svc.config_svc)`
    Help will be automatically available at /api, and will be based on the
    doc strings of the get/post/put/delete methods
    :param: **kwargs will be passed wen initializing the routes.
    """
    return [
        url(r"/api/1.0/versions", VersionsHandler, name="versions", kwargs=kwargs),
        url(r"/api/1.0/start/([\w_-]+)", StartHandler, name="start", kwargs=kwargs),
        url(r"/api/1.0/status/(\d*)", StatusHandler, name="status", kwargs=kwargs),
        url(r"/api/1.0/stop/([\d|all]*)", StopHandler, name="stop", kwargs=kwargs),
        url(r"/api/1.0/logs/([\w_-]+)", Bcl2FastqLogHandler, name="logs", kwargs=kwargs)
    ]

def start():
    """
    Start the bcl2fastq-ws app
    """

    app_svc = AppService.create(__package__)
    app_svc.start(routes(config=app_svc.config_svc))
