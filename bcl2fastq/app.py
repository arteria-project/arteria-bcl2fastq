
import tornado.ioloop
import tornado.web
from tornado.web import URLSpec as url
import click

from bcl2fastq.handlers.api_help_handlers import *
from bcl2fastq.handlers.bcl2fastq_handlers import *

from bcl2fastq.lib.config import Config


def create_app(debug=False, auto_reload=False):
    # TODO Move routes to separate file
    app = tornado.web.Application([
        url(r"/api/1.0", ApiHelpHandler, name="api"),
        url(r"/api/1.0/versions", VersionsHandler, name="versions"),
        url(r"/api/1.0/start/([\w_-]+)", StartHandler, name="start"),
        url(r"/api/1.0/status/(\d*)", StatusHandler, name="status"),
        url(r"/api/1.0/stop/([\d|all]*)", StopHandler, name="stop")
    ],
        debug=debug, auto_reload=auto_reload)
    return app

@click.command()
@click.option('--config', default="./bcl2fastq.config.yaml")
@click.option('--debug/--no-debug', default=False)
def start(config, debug):

    # This will ensure config is loaded through-out
    # the app.
    Config.load_config(config)

    # Start Tornado app.
    app = create_app(debug)
    app.listen(port = 8888)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    start()
