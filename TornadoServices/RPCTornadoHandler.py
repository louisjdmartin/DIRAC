from tornado.web import RequestHandler
from tornado.escape import json_encode, json_decode, url_unescape
import OpenSSL.crypto # TODO: Use M2CRYPTO
from DIRAC.Core.Security.ProxyInfo import getProxyInfo
from DIRAC.Core.Security.X509Certificate import X509Certificate
from DIRAC.Core.Security.X509Chain import X509Chain
import GSI
from DIRAC import S_OK, S_ERROR, gLogger


""" 
  Dummy handler who manage small database (1 table - Id:UserName)
  Method for RPC are at the end of the file
"""


class TornadoUserHandler(RequestHandler):

  
  def initialize(self, UserDB, AuthManager):
    """
      initialize

      :param UserDB: Handler connected to database, provided via dict in TornadoServer
      :param AuthManager: DIRAC authentification system
    """
    print('====== NEW REQUEST ======')
    self.userDB = UserDB
    self.authManager = AuthManager



  
  def prepare(self):
    """ 
      prepare
      Read the user certificate
    """
    self.credDict = self.gatherPeerCredentialsNoProxy()
    



  
  def post(self, procedure):
    """ 
    HTTP POST
      Call the method sended via URL and send returned value to client in JSON
      procedure is provided from the URL following rules from TornadoServer
      Arguments (if exists) for remote procedure call must be send in JSON by client

      :param str procedure: Name of the procedure we want to call
    """
    try:
      hardcodedAuth = getattr(self, 'auth_'+procedure)
    except AttributeError:
      hardcodedAuth = None
    if self.authManager.authQuery(procedure, self.credDict, hardcodedAuth):
      #Getting arguments, it can fail if args is not defined by client
      try:   
        args_encoded = self.get_argument('args')
        args = json_decode(args_encoded)
      except:
        args = []
      retVal = self._checkExpectedArgumentTypes(procedure, args)
      if retVal['OK']:
        # Executing method
        try:
          method = getattr(self, 'export_' + procedure)
          self.write(json_encode(method(*args)))
        except Exception, e:
          self.write(json_encode(S_ERROR(str(e))))
      else:
        gLogger.debug(retVal)
        self.write(json_encode(retVal))
    else:
      self.write(json_encode(S_ERROR("You're not authorized to do that.")))


  """ Copier coller du requesthandler dirac, voir pour eviter duplication de code """
  def _checkExpectedArgumentTypes(self, method, args):
    """
    Check that the arguments received match the ones expected

    :type method: string
    :param method: Method to check against
    :type args: tuple
    :param args: Arguments to check
    :return: S_OK/S_ERROR
    """
    sListName = "types_%s" % method
    try:
      oTypesList = getattr(self, sListName)
    except:
      gLogger.error("There's no types info for method", "export_%s" % method)
      return S_ERROR("Handler error for server %s while processing method %s" % (self.serviceInfoDict['serviceName'],
                                                                                 method))
    try:
      mismatch = False
      for iIndex in range(min(len(oTypesList), len(args))):
        # If None skip the parameter
        if oTypesList[iIndex] is None:
          continue
        # If parameter is a list or a tuple check types inside
        elif isinstance(oTypesList[iIndex], (tuple, list)):
          if not isinstance(args[iIndex], tuple(oTypesList[iIndex])):
            mismatch = True
        # else check the parameter
        elif not isinstance(args[iIndex], oTypesList[iIndex]):
          mismatch = True
        # Has there been a mismatch?
        if mismatch:
          sError = "Type mismatch in parameter %d (starting with param 0) Received %s, expected %s" % (
              iIndex, type(args[iIndex]), str(oTypesList[iIndex]))
          return S_ERROR(sError)
      if len(args) < len(oTypesList):
        return S_ERROR("Function %s expects at least %s arguments" % (method, len(oTypesList)))
    except Exception, v:
      sError = "Error in parameter check: %s" % str(v)
      gLogger.exception(sError)
      return S_ERROR(sError)
    return S_OK()


  def gatherPeerCredentialsNoProxy( self ):
    """
      Pour l'instant j'ai pas reussi a charger la chaine entiere...
      C'est du copier coller
      Et ca utilise GSI au lieu de M2Crypto...
    """
    peerChain = X509Certificate()
    peerChain.loadFromString(self.request.get_ssl_certificate(True), GSI.crypto.FILETYPE_ASN1)
    isProxyChain = False#peerChain.isProxy()['Value']
    isLimitedProxyChain = False#peerChain.isLimitedProxy()['Value']
    """if isProxyChain:
      if peerChain.isPUSP()['Value']:
        identitySubject = peerChain.getSubjectNameObject()[ 'Value' ] #peerChain.getCertInChain( -2 )['Value'].getSubjectNameObject()[ 'Value' ]
      else:
        identitySubject = peerChain.getIssuerCert()['Value'].getSubjectNameObject()[ 'Value' ]
    else: 
      identitySubject =  peerChain.getSubjectNameObject()[ 'Value' ]#peerChain.getCertInChain( 0 )['Value'].getSubjectNameObject()[ 'Value' ]
    """
    identitySubject =  peerChain.getSubjectNameObject()[ 'Value' ]#peerChain.getCertInChain( 0 )['Value'].getSubjectNameObject()[ 'Value' ]
    credDict = { 'DN' : identitySubject.one_line(),
                 'CN' : identitySubject.commonName,
                 'x509Chain' : peerChain,
                 'isProxy' : isProxyChain,
                 'isLimitedProxy' : isLimitedProxyChain }
    diracGroup = peerChain.getDIRACGroup()
    if diracGroup[ 'OK' ] and diracGroup[ 'Value' ]:
      credDict[ 'group' ] = diracGroup[ 'Value' ]
    return credDict












  auth_addUser = ['all']
  types_addUser = [(str, unicode)]
  def export_addUser(self, whom):
    """ 
    Add a user 

      :param str whom: The name of the user we want to add
      :return: S_OK with S_OK['Value'] = The_ID_of_the_user or S_ERROR
    """
    newUser = self.userDB.addUser(whom)
    if newUser['OK']:
      return S_OK(newUser['lastRowId'])
    return newUser

  auth_editUser = ['all']
  types_editUser = [int, (str, unicode)]
  def export_editUser(self, uid, value):
    """ 
      Edit a user 

      :param int uid: The Id of the user in database
      :param str value: New user name
      :return: S_OK or S_ERROR
    """
    return self.userDB.editUser(uid, value)


  auth_getUserName = ['all']
  types_getUserName = [int]
  def export_getUserName(self, uid):
    """ 
      Get a user 

      :param int uid: The Id of the user in database
      :return: S_OK with S_OK['Value'] = TheUserName or S_ERROR if not found
    """
    return self.userDB.getUserName(uid)


  auth_listUsers = ['nobody']
  types_listUsers = []
  def export_listUsers(self):
    """
      List all users

      :return: S_OK with S_OK['Value'] list of [UserId, UserName]
    """
    return self.userDB.listUsers()
