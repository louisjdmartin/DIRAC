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

from tornado.web import RequestHandler, MissingArgumentError

from DIRAC.Core.Security.X509Chain import X509Chain
from DIRAC.Core.DISET.AuthManager import AuthManager
from DIRAC.Core.DISET.private.ServiceConfiguration import ServiceConfiguration
from DIRAC.Core.DISET.private.LockManager import LockManager
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.Core.Utilities.JEncode import decode, encode
from DIRAC import S_OK, S_ERROR, gLogger
from DIRAC.Core.Utilities import Time
from DIRAC.Core.Utilities.DErrno import ENOAUTH
from DIRAC import gConfig
import DIRAC




class TornadoService(RequestHandler): #pylint: disable=abstract-method
  """
    TornadoService main class, manage all tornado services
    Instanciated at each request
  """
  __FLAG_INIT_DONE = False

  @classmethod
  def __initializeService(cls, url):
    """
      Initialize a service, called at first request
    """
    serviceName = url[1:]

    cls.log = gLogger
    cls._startTime = Time.dateTime()
    cls.log.info("First use of %s, initializing service..." % url)
    cls._authManager = AuthManager("%s/Authorization" % PathFinder.getServiceSection(serviceName))
    cls._cfg = ServiceConfiguration([serviceName])
    cls._lockManager = LockManager(cls._cfg.getMaxWaitingPetitions())
    cls._serviceName = serviceName
    cls._validNames = [serviceName]
    serviceInfo = {'serviceName': serviceName,
                   'serviceSectionPath': PathFinder.getServiceSection(serviceName),
                   'csPaths': [PathFinder.getServiceSection(serviceName)],
                   'URL': url
                  }
    cls._serviceInfoDict = serviceInfo

    try:
      cls.initializeHandler(serviceInfo)
    # If anything happen during initialization, we return the error
    except Exception as e: #pylint: disable=broad-except
      gLogger.error(e)
      error = S_ERROR('Error while initializing')
      for stack in error['CallStack']:
        gLogger.debug(stack)  # Display on log for debug
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

  def initialize(self, monitor, stats): #pylint: disable=arguments-differ
    """
      initialize, called at every request
      WARNING: DO NOT REWRITE THIS FUNCTION IN YOUR HANDLER
          ==> initialize in DISET became initializeRequest in HTTPS !
    """
    self.authorized = False
    self.method = None
    self._monitor = monitor
    self.stats = stats
    self.requestStartTime = time.time()
    stats['requests'] += 1
    self._monitor.setComponentExtraParam('queries', stats['requests'])
    self.credDict = None
    self.authorized = False
    self.method = None

    # try:
    #   self.monReport = self.__startReportToMonitoring()
    # except Exception:
    #   self.monReport = False

  def prepare(self):
    """
      prepare
      Check authorizations and get lock
    """

    # Init of service must be here, because if it crash we should be able to end request
    if not self.__FLAG_INIT_DONE:
      init = self.__initializeService(self.srv_getURL())
      if not init['OK']:
        del init['CallStack']  # Removed because happen before authentication, but displayed in server side
        self.set_status(500)
        self.write(encode(init))
        self.finish()

    self.credDict = self.gatherPeerCredentials()
    self._lockManager.lockGlobal()
    self.method = self.get_argument("method")
    self.initializeRequest()
    self.log.notice("Incoming request on /%s: %s" % (self._serviceName, self.method))
    try:
      hardcodedAuth = getattr(self, 'auth_' + self.method)
    except AttributeError:
      hardcodedAuth = None

    self.authorized = self._authManager.authQuery(self.method, self.credDict, hardcodedAuth)
    if not self.authorized:
      self.reportUnauthorizedAccess()

  def post(self): #pylint: disable=arguments-differ
    """
    HTTP POST, used for RPC
      Call the remote method, client may send his method via "method" argument
      and list of arguments in JSON in "args" argument
    """

    # Get arguments if exists
    try:
      args_encoded = self.get_body_argument('args')
    except MissingArgumentError:
      args = []
    args = decode(args_encoded)[0]

    # Execute the method
    try:
      self._lockManager.lock("RPC/%s" % self.method)
      method = getattr(self, 'export_%s' % self.method)
      try:
        retVal = method(*args)
        self.write(encode(retVal))
      except Exception as e:#pylint: disable=broad-except
        self.set_status(500)
        self.write(S_ERROR(e))

    except AttributeError as e:
      self.set_status(501)  # 501 = not implemented in HTTP
      self.write(encode(S_ERROR("Unknown method %s" % self.method)))

    finally:
      self._lockManager.unlock("RPC/%s" % self.method)

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
    if "CallStack" in error.keys():
      # If blocked because not authorized, client did not need server-side CallStack
      del error["CallStack"]

    # 401 is the error code for "Unauthorized" in HTTP
    # 403 is the error code for "Forbidden" in HTTP
    self.set_status(errorCode)
    self.write(encode(error))
    self.finish()

  def on_finish(self):
    """
      Called after the end of HTTP request
    """
    requestDuration = time.time() - self.requestStartTime
    gLogger.notice("Ending request to %s after %fs" % (self.srv_getURL(), requestDuration))
    self._lockManager.unlockGlobal()
    # if self.monReport:
    #   self.__endReportToMonitoring(*monReport)

  def gatherPeerCredentials(self):
    """
      Load client certchain in DIRAC and extract informations
    """
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
# Monitoring methods
#
####
  # def __startReportToMonitoring(self):
  #   self._monitor.addMark("Queries")
  #   now = time.time()
  #   stats = os.times()
  #   cpuTime = stats[0] + stats[2]
  #   if now - self.stats["monitorLastStatsUpdate"] < 0:
  #     return (now, cpuTime)
  #   # Send CPU consumption mark
  #   wallClock = now - self.__monitorLastStatsUpdate
  #   self.stats["monitorLastStatsUpdate"] = now
  #   # Send Memory consumption mark
  #   membytes = MemStat.VmB('VmRSS:')
  #   if membytes:
  #     mem = membytes / (1024. * 1024.)
  #     self._monitor.addMark('MEM', mem)
  #   return (now, cpuTime)

  # def __endReportToMonitoring(self, initialWallTime, initialCPUTime):
  #   wallTime = time.time() - initialWallTime
  #   stats = os.times()
  #   cpuTime = stats[0] + stats[2] - initialCPUTime
  #   percentage = cpuTime / wallTime * 100.
  #   if percentage > 0:
  #     self._monitor.addMark('CPU', percentage)


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
    # FROM DIRAC.Core.DISET.RequestHandler

    dInfo = {}
    dInfo['version'] = DIRAC.version
    dInfo['time'] = Time.dateTime()
    # Uptime
    try:
      with open("/proc/uptime") as oFD:
        iUptime = long(float(oFD.readline().split()[0].strip()))
      dInfo['host uptime'] = iUptime
    except BaseException:
      pass
    startTime = self._startTime
    dInfo['service start time'] = self._startTime
    serviceUptime = Time.dateTime() - startTime
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
    return credDict

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
