from tornado.web import RequestHandler
from tornado.escape import json_encode, url_unescape
from DIRAC.Core.Security import X509Chain
import OpenSSL.crypto
from time import time
from DIRAC.Core.Security.ProxyInfo import getProxyInfo

""" 
  This handler get Remote Requests and execute them
"""


class RPCTornadoHandler(RequestHandler):
  """
    initialize
    Get the services opened
    Get arguments from headers (if exists)
  """

  def initialize(self, DiracServices):
    self.DiracServices = DiracServices

    self.args = self.request.headers.get_list('args')
    for i in range(len(self.args)):
      self.args[i] = url_unescape(self.args[i])

  """ 
    prepare
    read the certificate
  """

  def prepare(self):
    """ Create a new class ? """
    x509 = X509Chain.X509Chain()
    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, self.request.get_ssl_certificate(True))

    certificate_subject = x509.get_subject().get_components()
    certificate_issuer = x509.get_issuer().get_components()
    certificate_not_after = x509.get_notAfter()
    certificate_group = x509.get_extension(1).get_data()

    print('============ USER CERTIFICATE ============')
    print('SUBJECT:')
    chain = ''
    for s in certificate_subject:
      chain += '/%s=%s' % (s[0], s[1])
    print chain

    chain = ''
    print('\nISSUER:')
    for s in certificate_issuer:
      chain += '/%s=%s' % (s[0], s[1])
    print chain
    print('\nEXPIRE: ' + certificate_not_after)
    print('\nGROUP:  ' + certificate_group)

  """ 
    HTTP GET
    Get the correct handler from a service already loaded and execute RPC Call
  """

  def get(self, service, procedure):
    print time() #Just to provide visual feedback when we repeat same request...
    print('============ HTTP GET Request ============')
    print('Service:   ' + service)
    print('Procedure: ' + procedure)
    print('Arguments: ' + str(self.args))
    print('==========================================')

    handler = self.DiracServices.getServiceHandler(service)

    if (handler == None):
      self.write(json_encode(S_ERROR('Service not started')))
      return

    """ Here the call can fail (Wrong  number of arguments for example) """
    try:
      method = getattr(handler, procedure)
      self.write(json_encode(method(*self.args)))
    except Exception, e:
      self.write(json_encode(S_ERROR(str(e))))
