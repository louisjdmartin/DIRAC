from tornado.web import RequestHandler
from tornado.escape import json_encode, url_unescape
from DIRAC.Core.Security import X509Chain
import OpenSSL.crypto
from DIRAC.Core.Security.ProxyInfo import getProxyInfo
from DIRAC import S_OK, S_ERROR


""" 
  Dummy handler who manage small database (1 table - Id:UserName)
  Method for RPC are at the end of the file
"""


class TornadoUserHandler(RequestHandler):

  """
    initialize
    UserDB is provided via dict in TornadoServer
  """
  def initialize(self, UserDB):
    self.userDB = UserDB


  """ 
    prepare
    Read the user certificate
    TODO: Read authorizations
  """
  def prepare(self):
    self.decodeUserCertificate()




  """ 
    HTTP GET
    Call the function sended via URL
    procedure is provided from the URL following rules from TornadoServer
    TODO: see if post can be better than get
  """
  def get(self, procedure):
    args_escaped = self.request.headers.get_list('args')
    args = [url_unescape(arg) for arg in args_escaped]    
    """ Here the call can fail (Wrong  number of arguments or non-defined function called for example) """
    try:
      method = getattr(self, 'export_' + procedure)
      self.write(json_encode(method(*args)))
    except Exception, e:
      self.write(json_encode(S_ERROR(str(e))))




  def decodeUserCertificate(self):
    """ TODO: use ProxyInfo.py """
    x509 = X509Chain.X509Chain()
    x509 = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_ASN1, 
            self.request.get_ssl_certificate(True)
           )
    self.certificate_subject = x509.get_subject().get_components()
    self.certificate_issuer = x509.get_issuer().get_components()
    self.certificate_not_after = x509.get_notAfter()
    self.certificate_group = x509.get_extension(1).get_data()

    print('============ USER CERTIFICATE ============')
    print('SUBJECT:')
    chain = ''
    for s in self.certificate_subject:
      chain += '/%s=%s' % (s[0], s[1])
    print chain

    chain = ''
    print('\nISSUER:')
    for s in self.certificate_issuer:
      chain += '/%s=%s' % (s[0], s[1])
    print chain
    print('\nEXPIRE: ' + self.certificate_not_after)
    print('\nGROUP:  ' + self.certificate_group)






  def export_addUser(self, whom):
    """ Add a user and return user id
    """
    newUser = self.userDB.addUser(whom)
    if newUser['OK']:
      return S_OK(newUser['lastRowId'])
    return newUser

  def export_removeUser(self, uid):
    """ Remove a user """
    return self.userDB.removeUser(uid)

  def export_editUser(self, uid, value):
    """ Edit a user """
    return self.userDB.editUser(uid, value)

  def export_getUserName(self, uid):
    """ Get a user """
    return self.userDB.getUserName(uid)

  def export_listUsers(self):
    return self.userDB.listUsers()
