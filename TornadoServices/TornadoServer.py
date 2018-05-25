"""
TORNADO SERVER
Receive RPC and return JSON to client





TODO Liste des trucs a voir:
- Comment lancer un service apres le lancement de tornardo ?
- Utiliser ServiceConfiguration (ish-OK)
- Utiliser LockManager (OK)
- Utiliser Monitoring  (Rien n'est fait)

"""

__RCSID__ = "$Id$"
from tornado.httpserver import HTTPServer
from tornado.web import Application, url
from tornado.ioloop import IOLoop
from tornado.util import import_object

from DIRAC import gLogger
from DIRAC.Core.DISET.AuthManager import AuthManager
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName, getSystemSection
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC.Core.DISET.private.LockManager import LockManager
from DIRAC.Core.DISET.private.ServiceConfiguration import ServiceConfiguration

import ssl
import os
import DIRAC
import urlparse


class TornadoServer():

  def __init__(self, services, debug=False, setup=None):
    if not isinstance(services, list):
      services = [services]
    self.urls = []
    self.services = []
    self.authManagers = {}
    self.lockManagers = {}
    self.cfgs = {}

    self.debug = debug
    self.setup = None
    self.rootURL = gConfigurationData.extractOptionFromCFG("/HTTPServer/rootURL")

    for service in services:
      self.addServiceToTornado(service)

  def addServiceToTornado(self, service):
    """
      Add a service to tornado

      :param str service: service name
    """
    self.authManagers[service] = AuthManager("%s/Authorization" % PathFinder.getServiceSection(service))
    self.cfgs[service] = ServiceConfiguration([service])
    self.lockManagers[service] = LockManager(self.cfgs[service].getMaxWaitingPetitions())
    self.__addURLToTornado(service)
    self.services.append(service)

  def __addURLToTornado(self, service):
    serviceTuple = divideFullName(service)
    serviceURL = r"%s%s" % (self.rootURL, service)
    self.urls.append(
        url(
            serviceURL,
            self.__getTornadoHandler(
                serviceTuple[1]),
            dict(
                AuthManager=self.authManagers[service],
                serviceName=service,
                LockManager=self.lockManagers[service],
                cfg=self.cfgs[service])))

  def __getTornadoHandler(self, service):
    # TODO recuperer des services autre part, comme dans DIRAC.FrameworkSystem.Service ou un truc du style
    gLogger.info("Intilializing handler for %s" % service)
    return getattr(import_object("DIRAC.TornadoServices.Service.%sHandler" % service), "%sHandler" % service)

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
    port = gConfigurationData.extractOptionFromCFG("/HTTPServer/port")
    gLogger.always("Listening on port %s" % port)
    for service in self.services:
      gLogger.always("Active service: %s" % service)

    try:
      server.listen(port)
      #server.start(0) # Fork process: 1/CPU, not sure if it's really safe
      IOLoop.current().start()
    except Exception as e:
      gLogger.fatal(e)

# TODO start with special script
#TornadoServer(["Framework/User", "Framework/Dummy"], debug=True).startTornado()
