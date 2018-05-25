from tornado.web import RequestHandler, MissingArgumentError
from tornado.escape import url_unescape
import OpenSSL.crypto  # TODO: Use M2CRYPTO
from DIRAC.Core.Security.ProxyInfo import getProxyInfo
from DIRAC.Core.Security.X509Certificate import X509Certificate
from DIRAC.Core.Security.X509Chain import X509Chain
import GSI
from DIRAC import S_OK, S_ERROR, gLogger
from DIRAC.Core.Utilities.JEncode import decode, encode
from tornado import gen
import time


class RPCTornadoHandler(RequestHandler):

  def initialize(self, AuthManager, serviceName, LockManager, cfg):
    """
      initialize
    """
    self.authManager = AuthManager
    self.authorized = False
    self.method = self.get_body_argument("method")
    self.credDict = self.gatherPeerCredentialsNoProxy()
    self.serviceName = serviceName
    self.LockManager = LockManager
    self.cfg = cfg

  def prepare(self):
    """
      prepare
      Check authorizations
    """
    self.LockManager.lockGlobal()
    gLogger.notice("Incoming request on %s: %s" % (self.serviceName, self.method))
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
      try:
        args_encoded = self.get_body_argument('args')
      except MissingArgumentError:
        args = []
      args = decode(args_encoded)[0]

      try:
        self.LockManager.lock("RPC/%s" % self.method)
        method = getattr(self, 'export_' + self.method)
        retVal = method(*args)
        self.write(encode(retVal))
      except e:
        self.write(encode(S_ERROR(str(e))))
      finally:
        self.LockManager.unlock("RPC/%s" % self.method)
    else:
      self.write(encode(S_ERROR("You're not authorized to do that.")))

  def on_finish(self):
    """
      Called after the end of HTTP request
    """
    self.LockManager.unlockGlobal()

  def gatherPeerCredentialsNoProxy(self):
    """
      Pour l'instant j'ai pas reussi a charger la chaine entiere...
      C'est du copier coller
      Et ca utilise GSI au lieu de M2Crypto...
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
