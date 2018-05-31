"""
TORNADO SERVER
Receive RPC and return JSON to client
"""

__RCSID__ = "$Id$"
from tornado.httpserver import HTTPServer
from tornado.web import Application, url
from tornado.ioloop import IOLoop
from DIRAC.Core.Utilities.ObjectLoader import ObjectLoader
from HandlerManager import HandlerManager

from DIRAC import gLogger, S_ERROR
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName, getSystemSection
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData

import ssl
import os
import DIRAC
import urlparse


class TornadoServer():

  def __init__(self, services=[], debug=False, setup=None):
    #TODO? initialize services with services argument ?

    if not isinstance(services, list):
      services = [services]
    # URLs for services: 1URL/Service
    self.urls = []
    self.services = []
    # Other infos
    self.debug = debug # Used only by tornado
    self.__objectLoader = ObjectLoader()
    self.setup = setup
    self.port = 443 # Default port for HTTPS, may be changed later...
    self.HandlerManager = HandlerManager()

    # Reading service list and add services
    # If we did not gave list of service, we start all services
    self.urls = self.HandlerManager.getHandlersURLs()

  def startTornado(self):
    """
      Start the tornado server when ready
      The script is blocked in the Tornado IOLoop
    """


    gLogger.debug("Starting Tornado")
    if(self.debug):
      gLogger.warn("TORNADO use debug mode, autoreload can generate unexpected effects, use it only in dev")

    router = Application(self.urls, debug=self.debug)

    cert_dir = "%s/etc/grid-security/" % DIRAC.rootPath

    # Define SSLContext
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH, cafile=os.path.join(cert_dir, "hostcert.pem"))

    # Force client to use certificate
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED

    # Load host certificates
    ssl_ctx.load_cert_chain(os.path.join(cert_dir, "hostcert.pem"),
                            os.path.join(cert_dir, "hostkey.pem"))

    # Start server
    server = HTTPServer(router, ssl_options=ssl_ctx)

    try:
      server.listen(self.port)
    except Exception as e:
      gLogger.fatal(e)
      return S_ERROR()
    gLogger.always("Listening on port %s" % self.port)
    for service in self.urls:
      gLogger.debug("Route: %s" % service)
    IOLoop.current().start()
