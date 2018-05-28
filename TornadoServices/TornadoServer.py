"""
TORNADO SERVER
Receive RPC and return JSON to client





TODO Liste des trucs a voir:
- Comment lancer un service apres le lancement de tornardo ?
- Utiliser ServiceConfiguration (a refaire pour tornado ?)
- Utiliser LockManager (OK)
- Utiliser Monitoring  

"""

__RCSID__ = "$Id$"
from tornado.httpserver import HTTPServer
from tornado.web import Application, url
from tornado.ioloop import IOLoop
from tornado.util import import_object

from DIRAC import gLogger
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName, getSystemSection
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData

import ssl
import os
import DIRAC
import urlparse


class TornadoServer():

  def __init__(self, services=[], debug=False, setup=None):
    if not isinstance(services, list):
      services = [services]

    # URLs for services: 1URL/Service
    self.urls = []
    self.services = []

    # Other infos
    self.debug = debug # Used only by tornado
    self.setup = setup

    # Reading service list and add services
    for service in services:
      self.addServiceToTornado(service)

  def addServiceToTornado(self, service):
    """
      Add a service to tornado before starting server
      Service can be called at https://<hostname>:<port>/<service>
                          e.g. https://dirac.cern.ch:1234/Framework/ServiceName

      :param str service: service name e.g. Framework/Name

    """
    # Register service in tornado
    self.__addURLToTornado(service)
    self.services.append(service)



  def __addURLToTornado(self, service):
    serviceURL = r"/%s" % service
    self.urls.append(url(serviceURL, self.__getTornadoHandlerAndInitialize(service)))
               


  def __getTornadoHandlerAndInitialize(self, service):
    serviceTuple = divideFullName(service)
    gLogger.info("Initilializing handler for %s" % service)

    # TODO recuperer des services autre part ? dans DIRAC.<quelquechose>System.Service ou un truc du style ?
    # Get the handler
    handler = getattr(import_object("DIRAC.TornadoServices.Service.%sHandler" % serviceTuple[1]), "%sHandler" % serviceTuple[1])

    # Initialize Service and handler
    # Service is the TornadoService, who get the request
    # Handler is the handler of the service with RPC method
    handler.initializeService(service, self.setup)
    handler.initializeHandler()
    return handler

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
    port = gConfigurationData.extractOptionFromCFG("/HTTPServer/Port")

    try:
      server.listen(port)
      gLogger.always("Listening on port %s" % port)

      for service in self.services:
        gLogger.always("Started service: %s" % service)
      IOLoop.current().start()
    except Exception as e:
      gLogger.fatal(e)

# TODO start with special script
#TornadoServer(["Framework/User", "Framework/Dummy"], debug=True).startTornado()
