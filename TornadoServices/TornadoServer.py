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
from DIRAC import gLogger, S_ERROR, S_OK
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName, getSystemSection
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC.FrameworkSystem.Client.MonitoringClient import MonitoringClient
from tornado.log import logging
from DIRAC.Core.Utilities import Time, MemStat
import time

import ssl
import os
import DIRAC
import urlparse


class TornadoServer():
  """
    Tornado webserver
    at init if we pass service list it will load only these services
    if not it will try yo discover all handlers available
  """

  def __init__(self, services=[], debug=False, setup=None):

    # TODO? initialize services with services argument ?

    if not isinstance(services, list):
      services = [services]
    # URLs for services: 1URL/Service
    self.urls = []
    # Other infos
    self.debug = debug  # Used only by tornado
    self.setup = setup
    self.port = 443  # Default port for HTTPS, may be changed later via config file ?
    self.HandlerManager = HandlerManager()
    self._monitor = MonitoringClient()
    self.stats = {'requests' : 0, 'monitorLastStatsUpdate':time.time()}
    # Reading service list and add services
    # If we did not gave list of service, we start all services
    if not services == []:
      self.HandlerManager.loadHandlersByServiceName(services)

    handlerDict = self.HandlerManager.getHandlersDict()
    for key in handlerDict.keys():
      self.urls.append(url(key, handlerDict[key], dict(monitor=self._monitor, stats=self.stats)))

  def startTornado(self):
    """
      Start the tornado server when ready
      The script is blocked in the Tornado IOLoop
    """

    gLogger.debug("Starting Tornado")
    self._initMonitoring()
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
      gLogger.debug("Available service: %s" % service)
    IOLoop.current().start()

  def _initMonitoring(self):
    # Init extra bits of monitoring
    self._monitor.setComponentType(MonitoringClient.COMPONENT_WEB)  # ADD COMPONENT TYPE FOR TORNADO ?
    self._monitor.initialize()

    self._monitor.registerActivity("Queries", "Queries served", "Framework", "queries", MonitoringClient.OP_RATE)
    self._monitor.registerActivity('CPU', "CPU Usage", 'Framework', "CPU,%", MonitoringClient.OP_MEAN, 600)
    self._monitor.registerActivity('MEM', "Memory Usage", 'Framework', 'Memory,MB', MonitoringClient.OP_MEAN, 600)
    self._monitor.registerActivity(
        'PendingQueries',
        "Pending queries",
        'Framework',
        'queries',
        MonitoringClient.OP_MEAN)

    self._monitor.setComponentExtraParam('DIRACVersion', DIRAC.version)
    self._monitor.setComponentExtraParam('platform', DIRAC.getPlatform())
    self._monitor.setComponentExtraParam('startTime', Time.dateTime())

    return S_OK()
