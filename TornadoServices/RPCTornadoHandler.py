from tornado.web import RequestHandler
from tornado.escape import json_encode, json_decode, url_unescape
import OpenSSL.crypto # TODO: Use M2CRYPTO
from DIRAC.Core.Security.ProxyInfo import getProxyInfo
from DIRAC.Core.Security.X509Certificate import X509Certificate
from DIRAC.Core.Security.X509Chain import X509Chain
import GSI
from DIRAC import S_OK, S_ERROR


""" 
  Dummy handler who manage small database (1 table - Id:UserName)
  Method for RPC are at the end of the file
"""


class TornadoUserHandler(RequestHandler):

  
  def initialize(self, UserDB, AuthManager):
    """
      initialize
      :param UserDB: Handler connected to database, provided via dict in TornadoServer
    """
    print('====== NEW REQUEST ======')
    self.userDB = UserDB
    self.authManager = AuthManager



  
  def prepare(self):
    """ 
      prepare
      Read the user certificate
      TODO: Read authorizations
    """
    self.credDict = self.gatherPeerCredentialsNoProxy()
    



  
  def post(self, procedure):
    """ 
    HTTP POST
      Call the function sended via URL and write the returned value to the connected client
      procedure is provided from the URL following rules from TornadoServer
      Arguments (if exists) for remote procedure call must be send in JSON by client
      :param str procedure: Name of the procedure we want to call
    """
    try:
      hardcodedAuth = getattr(self, 'auth_'+procedure)
    except AttributeError:
      hardcodedAuth = None
    if self.authManager.authQuery( procedure, self.credDict, hardcodedAuth ):
      #Getting arguments, it can fail if args is not defined by client
      try:   
        args_encoded = self.get_argument('args')
        args = json_decode(args_encoded)
      except:
        args = []
      print procedure
      print args

      # Here the call can fail (Wrong  number of arguments or non-defined function called for example) 
      try:
        method = getattr(self, 'export_' + procedure)
        self.write(json_encode(method(*args)))
      except Exception, e:
        self.write(json_encode(S_ERROR(str(e))))
    else:
      self.write(json_encode(S_ERROR("You're not authorized to do that.")))


  def decodeUserCertificate(self):
    # TODO: use ProxyInfo.py or M2CRYPTO 
    # Note used for now
    x509 = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_ASN1, 
            self.request.get_ssl_certificate(True)
           )
    credDict = {}
    self.certificate_subject = x509.get_subject().get_components()
    self.certificate_issuer = x509.get_issuer().get_components()
    self.certificate_not_after = x509.get_notAfter()
    try:
      self.certificate_group = x509.get_extension(1).get_data()
    except:
      self.certificate_group = 'unknown'
    print('============ USER CERTIFICATE ============')
    print('SUBJECT:')
    chain = ''
    for s in self.certificate_subject:
      chain += '/%s=%s' % (s[0], s[1])
      if(s[0] == 'CN'):
        credDict['CN'] = s[1]
    print chain
    credDict['DN'] = chain
    chain = ''
    print('ISSUER:')
    for s in self.certificate_issuer:
      chain += '/%s=%s' % (s[0], s[1])
    print chain
    print('EXPIRE: ' + self.certificate_not_after)
    print('GROUP:  ' + self.certificate_group)
    credDict['group'] = self.certificate_group


    # For now thesel infos are not real...
    credDict['isProxy'] = False
    credDict['isLimitedProxy'] = False
    return credDict
    return self.gatherPeerCredentials()

  def gatherPeerCredentialsNoProxy( self ):
    """
      Pour l'instant j'ai pas reussi a charger la chaine entiere...
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

  def export_editUser(self, uid, value):
    """ 
      Edit a user 
      :param int uid: The Id of the user in database
      :param str value: New user name
      :return: S_OK or S_ERROR
    """
    return self.userDB.editUser(uid, value)

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
