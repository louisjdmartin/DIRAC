"""
  TornadoService manage all services, your handler must inherith form this class
  TornadoService may be used only by TornadoServer.

  To create you must write this "minimal" code::

    from DIRAC.TornadoServices.Server.TornadoService import TornadoService
    class yourServiceHandler(TornadoService):

      @classmethod
      def initializeHandler(cls, infosDict):
        ## Called 1 time, at first request

      def initializeRequest(self):
        ## Called at each request

      auth_someMethod = ['all']
      def export_someMethod(self):
        #Insert your method here, don't forgot the return


  Then you must configure service like any other service

"""

import os
import time
from datetime import datetime
import concurrent.futures
from tornado.web import RequestHandler, MissingArgumentError, asynchronous
from tornado import gen
import tornado.ioloop
from tornado.ioloop import IOLoop

from DIRAC.TornadoServices.Utilities.b64Tornado import strDictTob64Dict, b64ListTostrList

import DIRAC
from DIRAC.Core.Security.X509Chain import X509Chain
from DIRAC.Core.DISET.AuthManager import AuthManager
from DIRAC.Core.DISET.private.ServiceConfiguration import ServiceConfiguration
from DIRAC.Core.DISET.private.LockManager import LockManager
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.Core.Utilities.JEncode import decode, encode
from DIRAC import S_OK, S_ERROR, gLogger
from DIRAC.Core.Utilities import MemStat
from DIRAC.Core.Utilities.DErrno import ENOAUTH
from DIRAC import gConfig
from DIRAC.FrameworkSystem.Client.MonitoringClient import MonitoringClient
from DIRAC.ConfigurationSystem.Client.PathFinder import getServiceURL




class TornadoService(RequestHandler): #pylint: disable=abstract-method
  """
    TornadoService main class, manage all tornado services
    Instanciated at each request
  """
  __FLAG_INIT_DONE = False

  # MonitoringClient, we don't use gMonitor which is not thread-safe
  # We also need to add specific attributes for each service
  _monitor = None


  @classmethod
  def flush_monitor(cls):
    #For tests, force to send more often
    cls._monitor.flush()


  @classmethod
  def _initMonitoring(cls, serviceName):

    # Init extra bits of monitoring
  
    cls._monitor = MonitoringClient()
    cls._monitor.setComponentType(MonitoringClient.COMPONENT_WEB)  # ADD COMPONENT TYPE FOR TORNADO ?


    cls._monitor.initialize()

    if tornado.process.task_id() is None: # Single process mode
      cls._monitor.setComponentName('Tornado/%s'%serviceName)
    else:
      cls._monitor.setComponentName('Tornado/CPU%d/%s'%(tornado.process.task_id(), serviceName))


    cls._monitor.setComponentLocation( cls._cfg.getURL() )

    cls._monitor.registerActivity( "Queries", "Queries served", "Framework", "queries", MonitoringClient.OP_RATE )


    cls._monitor.setComponentExtraParam('DIRACVersion', DIRAC.version)
    cls._monitor.setComponentExtraParam('platform', DIRAC.getPlatform())
    cls._monitor.setComponentExtraParam('startTime', datetime.utcnow())


    cls._stats = {'requests': 0, 'monitorLastStatsUpdate': time.time()}

    return S_OK()


  @classmethod
  def __initializeService(cls, url, fullUrl, debug):
    """
      Initialize a service, called at first request
    """
    serviceName = url[1:]

    if debug: # In debug mode we force monitoring to send data every 10 seconds
      tornado.ioloop.PeriodicCallback(cls.flush_monitor, 10000).start()
    # if not in debug mode, MonitoringClient sends data himself

    cls.debug = debug
    cls.log = gLogger
    cls._startTime = datetime.utcnow()
    cls.log.info("First use of %s, initializing service..." % url)
    cls._authManager = AuthManager("%s/Authorization" % PathFinder.getServiceSection(serviceName))
    cls._cfg = ServiceConfiguration([serviceName])

    cls._initMonitoring(serviceName)

    cls._serviceName = serviceName
    cls._validNames = [serviceName]
    serviceInfo = {'serviceName': serviceName,
                   'serviceSectionPath': PathFinder.getServiceSection(serviceName),
                   'csPaths': [PathFinder.getServiceSection(serviceName)],
                   'URL': fullUrl 
                  }
    cls._serviceInfoDict = serviceInfo

    cls.__monitorLastStatsUpdate = time.time()

    try:
      cls.initializeHandler(serviceInfo)
    # If anything happen during initialization, we return the error
    except Exception as e: #pylint: disable=broad-except
      gLogger.error(e)
      error = S_ERROR('Error while initializing')

      if self.debug:
        for stack in error['CallStack']:
          gLogger.debug(stack)  # Display on log for debug, because removed when sended to client
      return error

    cls.__FLAG_INIT_DONE = True
    return S_OK()



  @classmethod
  def initializeHandler(cls, serviceInfoDict):
    """
      This may be overwrited when you write a DIRAC service handler
      And it must be a class method. This method is called only one time
      during the initialization of the Tornado server
    """
    pass

  def initializeRequest(self):
    """
      Called at every request, may be overwrited
    """
    pass

  def initialize(self, debug): #pylint: disable=arguments-differ
    """
      initialize, called at every request
      WARNING: DO NOT REWRITE THIS FUNCTION IN YOUR HANDLER
          ==> initialize in DISET became initializeRequest in HTTPS !
    """
    self.debug = debug
    self.authorized = False
    self.method = None
    self.requestStartTime = time.time()
    self.credDict = None
    self.authorized = False
    self.method = None
    if not self.__FLAG_INIT_DONE:
      init = self.__initializeService(self.srv_getURL(), self.request.full_url(), debug)
      if not init['OK']:
        gLogger.debut("Error during initalization")
        gLogger.debug(init)
        return False


    self._stats['requests'] += 1
    #self._monitor.setComponentName(self.srv_getURL())
    self._monitor.setComponentExtraParam('queries', self._stats['requests'])
    self._monitor.addMark("Queries")

    
  def prepare(self):
    """
      prepare
    """

    # Init of service must be here, because if it crash we should be able to end request
    if not self.__FLAG_INIT_DONE:
      error = encode("Service can't be initialized !")
      del error['CallStack']
      self.write_return(error)
      self.finish()

    self.credDict = self.gatherPeerCredentials()
    self.method = self.get_argument("method")
    self.log.notice("Incoming request on /%s: %s" % (self._serviceName, self.method))
    try:
      hardcodedAuth = getattr(self, 'auth_' + self.method)
    except AttributeError:
      hardcodedAuth = None

    self.authorized = self._authManager.authQuery(self.method, self.credDict, hardcodedAuth)
    if not self.authorized:
      self.reportUnauthorizedAccess()

  @gen.coroutine
  def post(self): #pylint: disable=arguments-differ
    """
    HTTP POST, used for RPC
      Call the remote method, client may send his method via "method" argument
      and list of arguments in JSON in "args" argument
    """

    # Execute the method
    # None it's because we let Tornado manage the executor
    retVal = yield IOLoop.current().run_in_executor(None, self.__executeMethod)
   
    # Tornado recommend to write in main thread
    self.write_return(retVal.result())
    self.finish()

  @gen.coroutine
  def __executeMethod(self):

    # getting method
    try:
      method = getattr(self, 'export_%s' % self.method)
    except AttributeError as e:
      self.set_status(501)
      return S_ERROR("Unknown method %s" % self.method)

    #Decode args
    try:
      args_encoded = self.get_body_argument('args')
    except MissingArgumentError:
      args = []
    
    args = b64ListTostrList(decode(args_encoded)[0])

    #Execute
    try:
      self.initializeRequest()
      retVal = method(*args)
    except Exception as e:#pylint: disable=broad-except
      retVal = S_ERROR(e)
   
    return retVal




  def reportUnauthorizedAccess(self, errorCode=403):
    """
      This method stop the current request and return an error to client
      It uses HTTP 403 by default. 403 is used when authentication is done but you're not authorized
      401 is used before authentication (or problem during authentication)

      :param int errorCode: Error code, 403 is "Forbidden" and 401 is "Unauthorized"
    """
    error = S_ERROR(ENOAUTH, "Unauthorized query")
    gLogger.error(
        "Unauthorized access to %s: %s(%s) from %s" %
        (self.request.path,
         self.credDict['CN'],
         self.credDict['DN'],
         self.request.remote_ip))
    if "CallStack" in error:
      # If blocked because not authorized, client did not need server-side CallStack
      del error["CallStack"]

    # 401 is the error code for "Unauthorized" in HTTP
    # 403 is the error code for "Forbidden" in HTTP
    self.set_status(errorCode)
    self.write_return(error)
    self.finish()

  def on_finish(self):
    """
      Called after the end of HTTP request
    """
    requestDuration = time.time() - self.requestStartTime
    gLogger.notice("Ending request to %s after %fs" % (self.srv_getURL(), requestDuration))


  def write_return(self, dictionnary):
    """
      Write to client what we wan't to return to client, must be S_OK/S_ERROR
    """
    if not isinstance(dictionnary, dict):
      dictionnary = S_ERROR('Service returns incorrect type')
      del dictionnary['CallStack']
    self.write(encode(strDictTob64Dict(dictionnary)))

  def gatherPeerCredentials(self):
    """
      Load client certchain in DIRAC and extract informations
    """

    # TODO a remplacer
    chainAsText = self.request.connection.stream.socket.get_peer_cert().as_pem()
    peerChain = X509Chain()

    cert_chain = self.request.get_ssl_certificate_chain()
    for cert in cert_chain:
      chainAsText += cert.as_pem()
    peerChain.loadChainFromString(chainAsText)

    isProxyChain = peerChain.isProxy()['Value']
    isLimitedProxyChain = peerChain.isLimitedProxy()['Value']
    if isProxyChain:
      if peerChain.isPUSP()['Value']:
        identitySubject = peerChain.getCertInChain(-2)['Value'].getSubjectNameObject()['Value']
      else:
        identitySubject = peerChain.getIssuerCert()['Value'].getSubjectNameObject()['Value']
    else:
      identitySubject = peerChain.getCertInChain(0)['Value'].getSubjectNameObject()['Value']
    credDict = {'DN': identitySubject.one_line(),
                'CN': identitySubject.commonName,
                'x509Chain': peerChain,
                'isProxy': isProxyChain,
                'isLimitedProxy': isLimitedProxyChain}
    diracGroup = peerChain.getDIRACGroup()
    if diracGroup['OK'] and diracGroup['Value']:
      credDict['group'] = diracGroup['Value']
    if "extraCredentials" in self.request.arguments:
      extraCred = self.get_argument("extraCredentials")
      if extraCred:
        credDict['extraCredentials'] = decode(extraCred)[0]
    return credDict



####
#
#   Default method
#
####

  auth_ping = ['all']

  def export_ping(self):
    """
      Default ping method, returns some info about server
    """
    # COPY FROM DIRAC.Core.DISET.RequestHandler
    dInfo = {}
    dInfo['version'] = DIRAC.version
    dInfo['time'] = datetime.utcnow()
    # Uptime
    try:
      with open("/proc/uptime") as oFD:
        iUptime = long(float(oFD.readline().split()[0].strip()))
      dInfo['host uptime'] = iUptime
    except BaseException:
      pass
    startTime = self._startTime
    dInfo['service start time'] = self._startTime
    serviceUptime = datetime.utcnow() - startTime
    dInfo['service uptime'] = serviceUptime.days * 3600 + serviceUptime.seconds
    # Load average
    try:
      with open("/proc/loadavg") as oFD:
        sLine = oFD.readline()
      dInfo['load'] = " ".join(sLine.split()[:3])
    except BaseException:
      pass
    dInfo['name'] = self._serviceInfoDict['serviceName']
    stTimes = os.times()
    dInfo['cpu times'] = {'user time': stTimes[0],
                          'system time': stTimes[1],
                          'children user time': stTimes[2],
                          'children system time': stTimes[3],
                          'elapsed real time': stTimes[4]
                         }


    #print "CHRIS ping return"
    return S_OK(dInfo)

  auth_echo = ['all']

  @staticmethod
  def export_echo(data):
    """
    This method used for testing the performance of a service
    """
    return S_OK(data)

  auth_whoami = ['all']

  def export_whoami(self):
    """
      Default whoami method, returns credentialDictionnary
    """
    credDict = self.srv_getRemoteCredentials()
    if 'x509Chain' in credDict:
      del credDict['x509Chain']  # Not serializable
    return S_OK(credDict)

  def getConfig(self):
    """ Return configuration
    """
    return self._cfg

####
#
#  Utilities methods
#  From DIRAC.Core.DISET.requestHandler to get same interface
#  Adapted for Tornado
#  Some function return warning, it's for prevent forgots when porting service to tornado
#  by "copy-paste" or just modify the imports
#
####

  @classmethod
  def srv_getCSOption(cls, optionName, defaultValue=False):
    """
    Get an option from the CS section of the services

    :return: Value for serviceSection/optionName in the CS being defaultValue the default
    """
    if optionName[0] == "/":
      return gConfig.getValue(optionName, defaultValue)
    for csPath in cls._serviceInfoDict['csPaths']:
      result = gConfig.getOption("%s/%s" % (csPath, optionName, ), defaultValue)
      if result['OK']:
        return result['Value']
    return defaultValue

  def getCSOption(self, optionName, defaultValue=False):
    """
      Just for keeping same public interface
    """
    return self.srv_getCSOption(optionName, defaultValue)

  def srv_getRemoteAddress(self):
    """
    Get the address of the remote peer.

    :return: Address of remote peer.
    """
    return self.request.remote_ip

  def getRemoteAddress(self):
    """
      Just for keeping same public interface
    """
    return self.srv_getRemoteAddress()

  def srv_getRemoteCredentials(self):
    """
    Get the credentials of the remote peer.

    :return: Credentials dictionary of remote peer.
    """
    return self.credDict
  def getRemoteCredentials(self):
    """
    Get the credentials of the remote peer.

    :return: Credentials dictionary of remote peer.
    """
    return self.credDict

  def srv_getFormattedRemoteCredentials(self):
    """
      Return the DN of user
    """
    try:
      return self.credDict['DN']
    except KeyError:  # Called before reading certificate chain
      return "unknown"


  def srv_getServiceName(self):
    """
      Return the service name
    """
    return self._serviceInfoDict['serviceName']




  def srv_getURL(self):
    """
      Return the URL
    """
    return self.request.path



def getServiceOption(serviceInfo, optionName, defaultValue):
  """ Get service option resolving default values from the master service

  WARNING: COPY PASTE FROM DIRAC/Core/DISET/RequestHandler.py
  """
  if optionName[0] == "/":
    return gConfig.getValue(optionName, defaultValue)
  for csPath in serviceInfo['csPaths']:
    result = gConfig.getOption("%s/%s" % (csPath, optionName, ), defaultValue)
    if result['OK']:
      return result['Value']
  return defaultValue
