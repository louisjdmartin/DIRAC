from tornado.web import RequestHandler, MissingArgumentError
from DIRAC.Core.Security.X509Certificate import X509Certificate
from DIRAC.Core.DISET.AuthManager import AuthManager
from DIRAC.Core.DISET.private.ServiceConfiguration import ServiceConfiguration
from DIRAC.Core.DISET.private.LockManager import LockManager
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.Core.Utilities.JEncode import decode, encode
from DIRAC import S_OK, S_ERROR, gLogger
from tornado import gen

# TODO: Use M2CRYPTO
import GSI


class TornadoService(RequestHandler):
  __FLAG_INIT = False
  @classmethod
  def initializeService(cls, serviceName, setup=None):
    gLogger.warn("INIT")
    cls.__FLAG_INIT_DONE = True
    cls.authManager = AuthManager("%s/Authorization" % PathFinder.getServiceSection(serviceName))
    cls.cfg = ServiceConfiguration([serviceName]) # TODO Use Tornado ServiceConfiguration ? (Cf. Workplan)
    cls.lockManager = LockManager(cls.cfg.getMaxWaitingPetitions())
    cls.serviceName = serviceName
    cls.initializeHandler()

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
      gLogger.info("First use of %s, initializing service..." % self.request.path)
      self.initializeService(self.request.path[1:])
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
    gLogger.notice("Incoming request on /%s: %s" % (self.serviceName, self.method))
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
      self.write(encode(S_ERROR("You're not authorized to do that.")))

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
    """
    peerChain = X509Certificate()
    peerChain.loadFromString(self.request.get_ssl_certificate(True), GSI.crypto.FILETYPE_ASN1)
    isProxyChain = False  # peerChain.isProxy()['Value']
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
