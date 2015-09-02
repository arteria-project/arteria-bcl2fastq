
from arteria.web.app import AppService
from bcl2fastq.handlers.bcl2fastq_handlers import *
from tornado.web import URLSpec as url
import logging

# Setup the routing. Help will be automatically available at /api, and will be based on
# the doc strings of the get/post/put/delete methods

def routes(**kwargs):
    routes = [
        url(r"/api/1.0/versions", VersionsHandler, name="versions", kwargs=kwargs),
        url(r"/api/1.0/start/([\w_-]+)", StartHandler, name="start", kwargs=kwargs),
        url(r"/api/1.0/status/(\d*)", StatusHandler, name="status", kwargs=kwargs),
        url(r"/api/1.0/stop/([\d|all]*)", StopHandler, name="stop", kwargs=kwargs)
    ]
    return routes

def start():

    log = logging.getLogger(__name__)

    app_svc = AppService.create(__package__)

    app_svc.start(routes(config=app_svc.config_svc))
