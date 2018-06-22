"""
TornadoServer create a web server and load services. It may work better with TornadoClient but as it accepts HTTPS you can create your own client
"""

__RCSID__ = "$Id$"


import time
from socket import error as socketerror
import M2Crypto

# Patching -- Should disable pylint wrong-import-position...
from tornado_m2crypto.m2netutil import m2_wrap_socket # pylint: disable=wrong-import-position
import tornado.netutil # pylint: disable=wrong-import-position
tornado.netutil.ssl_wrap_socket = m2_wrap_socket # pylint: disable=wrong-import-position

import tornado.httputil # pylint: disable=wrong-import-position
tornado.httputil.HTTPServerRequest.configure('tornado_m2crypto.m2httputil.M2HTTPServerRequest') # pylint: disable=wrong-import-position
import tornado.iostream # pylint: disable=wrong-import-position
tornado.iostream.SSLIOStream.configure('tornado_m2crypto.m2iostream.M2IOStream') # pylint: disable=wrong-import-position

from tornado.httpserver import HTTPServer
from tornado.web import Application, url
from tornado.ioloop import IOLoop


from DIRAC.TornadoServices.Server.HandlerManager import HandlerManager
from DIRAC import gLogger, S_ERROR
from DIRAC.FrameworkSystem.Client.MonitoringClient import MonitoringClient
from DIRAC.Core.Security import Locations







class TornadoServer(object):
  """
    Tornado webserver

    Initialize and run a HTTPS Server for DIRAC services.
    By default it load all services from configuration, but you can also give an explicit list.
    If you gave explicit list of services, only these ones are loaded

    Example 1: Easy way to start tornado::

      # Initialize server and load services
      serverToLaunch = TornadoServer()

      # Start listening when ready
      serverToLaunch.startTornado()

    Example 2:We want to debug service1 and service2 only, and use another port for that ::

      services = ['component/service1', 'component/service2']
      serverToLaunch = TornadoServer(services=services, port=1234, debug=True)
      serverToLaunch.startTornado()
  """

  def __init__(self, services=None, debug=False, port=443):
    """
    :param list services: List of services you want to start, start all by default
    :param str debug: Activate debug mode of Tornado (autoreload server + more errors display) and M2Crypto
    :param int port: Used to change port, default is 443
    """

    if services and not isinstance(services, list):
      services = [services]
    # URLs for services: 1URL/Service
    self.urls = []
    # Other infos
    self.debug = debug  # Used by tornado and M2Crypto
    self.port = port
    self.handlerManager = HandlerManager()
    self._monitor = MonitoringClient()
    self.stats = {'requests': 0, 'monitorLastStatsUpdate': time.time()}

    # If services are defined, load only these ones (useful for debug purpose)
    if services and services != []:
      self.handlerManager.loadHandlersByServiceName(services)

    # if no service list is given, load services from configuration
    handlerDict = self.handlerManager.getHandlersDict()
    for key in handlerDict:
      # handlerDict[key].initializeService(key)
      self.urls.append(url(key, handlerDict[key], dict(monitor=self._monitor, stats=self.stats)))

  def startTornado(self, multiprocess=True):
    """
      Start the tornado server when ready.
      The script is blocked in the Tornado IOLoop.
      Multiprocess option is available, not active by default.
    """

    gLogger.debug("Starting Tornado")
    #self._initMonitoring()

    if self.debug:
      gLogger.warn("TORNADO use debug mode, autoreload can generate unexpected effects, use it only in dev")

    router = Application(self.urls, debug=self.debug)

    certs = Locations.getHostCertificateAndKeyLocation()

    ca = Locations.getCAsLocation()

    ssl_options = {
        'certfile': certs[0],
        'keyfile': certs[1],
        'cert_reqs': M2Crypto.SSL.verify_peer,
        'ca_certs': ca,
        'sslDebug' : self.debug
    }

    # Start server
    server = HTTPServer(router, ssl_options=ssl_options)
    try:
      if multiprocess:
        server.bind(self.port)
      else:
        server.listen(self.port)
    except socketerror as e:
      gLogger.fatal(e)
      return S_ERROR()
    gLogger.always("Listening on port %s" % self.port)
    for service in self.urls:
      gLogger.debug("Available service: %s" % service)
    if multiprocess:
      server.start(0)
      IOLoop.current().start()
    else:
      IOLoop.instance().start()
    return True #Never called because of IOLoop, but to make pylint happy

  # def _initMonitoring(self):
  #   # Init extra bits of monitoring
  #

  #   self._monitor.setComponentType(MonitoringClient.COMPONENT_WEB)  # ADD COMPONENT TYPE FOR TORNADO ?
  #   self._monitor.initialize()

  #   self._monitor.registerActivity("Queries", "Queries served", "Framework", "queries", MonitoringClient.OP_RATE)
  #   self._monitor.registerActivity('CPU', "CPU Usage", 'Framework', "CPU,%", MonitoringClient.OP_MEAN, 600)
  #   self._monitor.registerActivity('MEM', "Memory Usage", 'Framework', 'Memory,MB', MonitoringClient.OP_MEAN, 600)

  #   self._monitor.setComponentExtraParam('DIRACVersion', DIRAC.version)
  #   self._monitor.setComponentExtraParam('platform', DIRAC.getPlatform())
  #   self._monitor.setComponentExtraParam('startTime', Time.dateTime())

  #   return S_OK()
