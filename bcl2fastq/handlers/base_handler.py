
import jsonpickle
from tornado.web import RequestHandler

class BaseHandler(RequestHandler):
    """
    Handler base class providing utility methods
    """

    def write_object(self, obj):
        """
        Encode obj as json and write it.
        :param obj: to output as json
        :return: nothing
        """
        resp = jsonpickle.encode(obj, unpicklable=False)
        self.write_json(resp)

    def write_json(self, json):
        """
        Write json with while seeting the content type to application/json
        :param json: to write
        :return: nothing
        """
        self.set_header("Content-Type", "application/json")
        self.write(json)

    def api_link(self, version="1.0"):
        """
        Base for the api
        :param version: api version
        :return: the api version string
        """
        return "%s://%s/api/%s" % (self.request.protocol, self.request.host, version)