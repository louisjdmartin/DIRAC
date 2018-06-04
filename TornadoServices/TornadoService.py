from tornado.web import RequestHandler, MissingArgumentError
from DIRAC.Core.Security.X509Certificate import X509Certificate
from DIRAC.Core.Security.X509Chain import X509Chain
from DIRAC.Core.DISET.AuthManager import AuthManager
from DIRAC.Core.DISET.private.ServiceConfiguration import ServiceConfiguration
from DIRAC.Core.DISET.private.LockManager import LockManager
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.Core.Utilities.JEncode import decode, encode
from DIRAC import S_OK, S_ERROR, gLogger
from tornado import gen

# TODO: Use M2CRYPTO
import GSI
import ssl


class TornadoService(RequestHandler):
  __FLAG_INIT = False

  @classmethod
  def initializeService(cls, serviceName, url, setup=None):
    cls.__FLAG_INIT_DONE = True
    cls.authManager = AuthManager("%s/Authorization" % PathFinder.getServiceSection(serviceName))
    cls.cfg = ServiceConfiguration([serviceName])  # TODO Use Tornado ServiceConfiguration ? (Cf. Workplan)
    cls.lockManager = LockManager(cls.cfg.getMaxWaitingPetitions())
    cls.serviceName = serviceName
    cls.initializeHandler()
    cls.log = gLogger
    cls._serviceInfoDict = {'serviceName': serviceName,
                            'serviceSectionPath': PathFinder.getServiceSection(serviceName),
                            #'validNames' : self._validNames,
                            #'csPaths' : [ PathFinder.getServiceSection( svcName ) for svcName in self._validNames ]
                            }

    cls.log.info("First use of %s, initializing service..." % url)

  @classmethod
  def initializeHandler(cls):
    """
      This may be overwrited when you write a DIRAC service handler
      And it must be a class method. This method is called only one time
      during the initialization of the Tornado server

      TODO: Implement "ServiceInfo" argument
    """
    pass

  def initialize(self):
    """
      initialize, called at every request
    """
    if not self.__FLAG_INIT:
      # remove the initial "/"
      self.initializeService(self.request.path[1:], self.request.path)
    self.authorized = False
    self.method = None
    self.credDict = self.gatherPeerCredentialsNoProxy()

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
    except e:
      self.write(encode(S_ERROR(str(e))))
    finally:
      self.lockManager.unlock("RPC/%s" % self.method)

  def on_finish(self):
    """
      Called after the end of HTTP request
    """
    self.lockManager.unlockGlobal()

  def gatherPeerCredentialsNoProxy(self):
    """
      Pour l'instant j'ai pas reussi a charger la chaine entiere...
      C'est du copier coller et ca utilise GSI au lieu de M2Crypto...
      Il faudra changer ca avec la vrai lecture de certificats

      Il faut aussi remplir le serviceInfoDict ou ajouter un dict (hors variable de classe)
      avec les infos pour les fonctions srv_getClientSetup / srv_getClientVO
    """
    peerChain = X509Certificate()
    peerChain.loadFromString(self.request.get_ssl_certificate(True), GSI.crypto.FILETYPE_ASN1)

    certList = X509Chain()
    # print certList.loadChainFromString(self.request.get_ssl_certificate(True), GSI.crypto.FILETYPE_ASN1)
    #print (certList.isProxy())
    isProxyChain = False  # certList.isProxy()['Value']
    isLimitedProxyChain = False  # peerChain.isLimitedProxy()['Value']
    """if isProxyChain:
      if peerChain.isPUSP()['Value']:
        identitySubject = peerChain.getSubjectNameObject()[ 'Value' ] #peerChain.getCertInChain( -2 )['Value'].getSubjectNameObject()[ 'Value' ]
      else:
        identitySubject = peerChain.getIssuerCert()['Value'].getSubjectNameObject()[ 'Value' ]
    else:
      identitySubject =  peerChain.getSubjectNameObject()[ 'Value' ]#peerChain.getCertInChain( 0 )['Value'].getSubjectNameObject()[ 'Value' ]
    """
    identitySubject = peerChain.getSubjectNameObject(
    )['Value']  # peerChain.getCertInChain( 0 )['Value'].getSubjectNameObject()[ 'Value' ]
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
    return cls.serviceSection['serviceName']
  """
  TODO: Reimplement sericeInfoDict

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
    gLogger.warn("You're using old interface, please update your script, you are using interface from DISET requestHandler")
    return self.request.path

  @classmethod
  def srv_getMonitor(cls):
    return cls.__monitor

  def srv_msgReply(self, msgObj):
    gLogger.warn("This method (srv_msgReply) does not exist in Tornado requesthandler, you are using interface from DISET requestHandler, please use self.write() if needed")
    return S_ERROR(
        "This method does not exist in Tornado requesthandler, you are using interface from DISET requestHandler, please use self.write if needed")

  @classmethod
  def srv_msgSend(cls, trid, msgObj):
    gLogger.warn("This method (srv_msgReply) does not exist in Tornado requesthandler, you are using interface from DISET requestHandler, please use self.write() if needed")
    return S_ERROR(
        "This method does not exist in Tornado requesthandler, you are using interface from DISET requestHandler, please use self.write if needed")

  @classmethod
  def srv_msgCreate(cls, msgName):
    gLogger.warn(
        "This method (srv_msgCreate) does not exist in Tornado requesthandler, you are using interface from DISET requestHandler")
    return S_ERROR("This method does not exist in Tornado requesthandler, you are using interface from DISET requestHandler")

  @classmethod
  def srv_disconnectClient(cls, trid):
    gLogger.warn(
        "This method (srv_disconnectClient) does not exist in Tornado requesthandler, you are using interface from DISET requestHandler")
    return S_ERROR("This method does not exist in Tornado requesthandler, you are using interface from DISET requestHandler")

  def srv_disconnect(self, trid=None):
    gLogger.warn(
        "This method (srv_disconnect) does not exist in Tornado requesthandler, you are using interface from DISET requestHandler")
    return S_ERROR("This method does not exist in Tornado requesthandler, you are using interface from DISET requestHandler")
