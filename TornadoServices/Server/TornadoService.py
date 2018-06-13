from tornado.web import RequestHandler, MissingArgumentError
from DIRAC.Core.Security.X509Certificate import X509Certificate
from DIRAC.Core.Security.X509Chain import X509Chain
from DIRAC.Core.DISET.AuthManager import AuthManager
from DIRAC.Core.DISET.private.ServiceConfiguration import ServiceConfiguration
from DIRAC.Core.DISET.private.LockManager import LockManager
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.Core.Utilities.JEncode import decode, encode
from DIRAC import S_OK, S_ERROR, gLogger
from DIRAC.Core.Security.ProxyInfo import getProxyInfo

from tornado import gen

# TODO: Use M2CRYPTO
import GSI
import ssl


class TornadoService(RequestHandler):
  __FLAG_INIT_DONE = False

  @classmethod
  def initializeService(cls, url, setup=None):
    serviceName = url[1:]

    cls.log = gLogger
    cls.log.info("First use of %s, initializing service..." % url)
    cls.__FLAG_INIT_DONE = True
    cls.authManager = AuthManager("%s/Authorization" % PathFinder.getServiceSection(serviceName))
    cls._cfg = ServiceConfiguration([serviceName])
    cls.lockManager = LockManager(cls._cfg.getMaxWaitingPetitions())
    cls.serviceName = serviceName
    cls._validNames = [serviceName]
    serviceInfo = {'serviceName': serviceName,
                   'serviceSectionPath': PathFinder.getServiceSection(serviceName),
                   'csPaths': [PathFinder.getServiceSection(serviceName)]
                   }
    cls._serviceInfoDict = serviceInfo
    cls.initializeHandler(serviceInfo)

  @classmethod
  def initializeHandler(cls, serviceInfoDict):
    """
      This may be overwrited when you write a DIRAC service handler
      And it must be a class method. This method is called only one time
      during the initialization of the Tornado server
    """
    pass

  def initialize(self, monitor, stats):
    """
      initialize, called at every request
    """

    self.authorized = False
    self.method = None
    self._monitor = monitor
    self.credDict = self.gatherPeerCredentials()
    stats['requests'] += 1
    self._monitor.setComponentExtraParam('queries', stats['requests'])
    self.stats = stats

    try:
      self.monReport = self.__startReportToMonitoring()
    except Exception:
      self.monReport = False

  def prepare(self):
    """
      prepare
      Check authorizations
    """
    self.lockManager.lockGlobal()
    self.method = self.get_argument("method")
    self.log.notice("Incoming request on /%s: %s" % (self.serviceName, self.method))
    try:
      hardcodedAuth = getattr(self, 'auth_' + self.method)
    except AttributeError:
      hardcodedAuth = None
    self.authorized = self.authManager.authQuery(self.method, self.credDict, hardcodedAuth)

  def post(self):
    """
    HTTP POST
      Call the remote method, client may send his method via "method" argument
      and list of arguments in JSON in "args" argument
    """

    if self.authorized:
      self.__execute_RPC()

    else:
      error = S_ERROR("You're not authorized to do that.")
      gLogger.warn(
          "Unauthorized access to %s: %s(%s) from %s" %
          (self.request.path,
           self.credDict['CN'],
           self.credDict['DN'],
           self.request.remote_ip))
      if "CallStack" in error.keys():
        # If blocked because not authorized, client did not need server-side CallStack
        del error["CallStack"]

      # 401 is the error code for "Unauthorized" in HTTP
      self.set_status(401)
      self.write(encode(error))

  def __execute_RPC(self):
    # Get arguments if exists
    try:
      args_encoded = self.get_body_argument('args')
    except MissingArgumentError:
      args = []
    args = decode(args_encoded)[0]

    # Execute the method
    try:
      self.lockManager.lock("RPC/%s" % self.method)
      method = getattr(self, 'export_' + self.method)
      retVal = method(*args)
      self.write(encode(retVal))
    except Exception as e:
      # If we try to ping server, can be redifined be defining a export_ping method
      if(self.method == 'ping'):
        self.write(encode(S_OK('pong')))
      else:
        self.write(encode(S_ERROR(str(e))))
    finally:
      self.lockManager.unlock("RPC/%s" % self.method)

  def on_finish(self):
    """
      Called after the end of HTTP request
    """
    self.lockManager.unlockGlobal()
    if self.monReport:
      self.__endReportToMonitoring(*monReport)

  def gatherPeerCredentials(self):
    """
      Load client certchain in DIRAC and extract informations
    """
    chainAsText = self.request.connection.stream.socket.get_peer_cert().as_pem()
    peerChain = X509Chain()

    cert_chain = self.request.connection.stream.socket.get_peer_cert_chain()
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

    return credDict

####
#
# Monitoring methods
#
####
  def __startReportToMonitoring(self):
    self._monitor.addMark("Queries")
    now = time.time()
    stats = os.times()
    cpuTime = stats[0] + stats[2]
    if now - self.stats["monitorLastStatsUpdate"] < 0:
      return (now, cpuTime)
    # Send CPU consumption mark
    wallClock = now - self.__monitorLastStatsUpdate
    self.stats["monitorLastStatsUpdate"] = now
    # Send Memory consumption mark
    membytes = MemStat.VmB('VmRSS:')
    if membytes:
      mem = membytes / (1024. * 1024.)
      self._monitor.addMark('MEM', mem)
    return (now, cpuTime)

  def __endReportToMonitoring(self, initialWallTime, initialCPUTime):
    wallTime = time.time() - initialWallTime
    stats = os.times()
    cpuTime = stats[0] + stats[2] - initialCPUTime
    percentage = cpuTime / wallTime * 100.
    if percentage > 0:
      self._monitor.addMark('CPU', percentage)


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
    for csPath in cls.__srvInfoDict['csPaths']:
      result = gConfig.getOption("%s/%s" % (csPath, optionName, ), defaultValue)
      if result['OK']:
        return result['Value']
    return defaultValue

  def srv_getRemoteAddress(self):
    """
    Get the address of the remote peer.

    :return: Address of remote peer.
    """
    return self.request.remote_ip

  def srv_getRemoteCredentials(self):
    """
    Get the credentials of the remote peer.

    :return: Credentials dictionary of remote peer.
    """
    return self.credDict

  def srv_getFormattedRemoteCredentials(self):
    try:
      return self.credDict['DN']
    except KeyError:  # Called before reading certificate chain
      return "unknown"

  def srv_getTransportID(self):
    gLogger.warn(
        "This method (srv_getTransportID) does not exist in Tornado requesthandler, you are using interface from DISET requestHandler")
    return S_ERROR("This method does not exist in Tornado requesthandler")

  def srv_getServiceName(cls):
    return cls._serviceInfoDict['serviceName']
  """
  TODO: Reimplement serviceInfoDict

  def srv_getClientSetup(self):
    return self.serviceInfoDict['clientSetup']

  def srv_getClientVO(self):
    return self.serviceInfoDict['clientVO']


  """

  def srv_getActionTuple(self):
    gLogger.warn(
        "This method (srv_getActionTuple) does not exist in Tornado requesthandler, you are using interface from DISET requestHandler")
    return S_ERROR("This method does not exist in Tornado requesthandler, you are using interface from DISET requestHandler")

  def srv_getURL(self):
    return self.request.path
  """
  @classmethod
  def srv_getMonitor(cls):
    return cls.__monitor
  """
