from tornado.web import RequestHandler
from tornado.escape import json_encode, json_decode, url_unescape
import OpenSSL.crypto # TODO: Use M2CRYPTO
from DIRAC.Core.Security.ProxyInfo import getProxyInfo
from DIRAC import S_OK, S_ERROR


""" 
  Dummy handler who manage small database (1 table - Id:UserName)
  Method for RPC are at the end of the file
"""


class TornadoUserHandler(RequestHandler):

  
  def initialize(self, UserDB):
    """
      initialize
      :param UserDB: Handler connected to database, provided via dict in TornadoServer
    """
    self.userDB = UserDB


  
  def prepare(self):
    """ 
      prepare
      Read the user certificate
      TODO: Read authorizations
    """
    self.decodeUserCertificate()



  
  def post(self, procedure):
    """ 
    HTTP POST
      Call the function sended via URL and write the returned value to the connected client
      procedure is provided from the URL following rules from TornadoServer
      Arguments (if exists) for remote procedure call must be send in JSON by client
      :param str procedure: Name of the procedure we want to call
    """

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




  def decodeUserCertificate(self):
    # TODO: use ProxyInfo.py or M2CRYPTO 
    x509 = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_ASN1, 
            self.request.get_ssl_certificate(True)
           )
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
    print chain

    chain = ''
    print('ISSUER:')
    for s in self.certificate_issuer:
      chain += '/%s=%s' % (s[0], s[1])
    print chain
    print('EXPIRE: ' + self.certificate_not_after)
    print('GROUP:  ' + self.certificate_group)






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

  def export_listUsers(self):
    """
      List all users
      :return: S_OK with S_OK['Value'] list of [UserId, UserName]
    """
    return self.userDB.listUsers()
