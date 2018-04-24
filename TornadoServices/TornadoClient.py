from tornado.httputil import HTTPHeaders
from tornado.httpclient import HTTPRequest, HTTPResponse,HTTPClient, AsyncHTTPClient
from tornado.escape import json_decode,url_escape
from tornado import ioloop
import os, ssl
from DIRAC.Core.Utilities.Proxy import executeWithUserProxy
import DIRAC.Core.Security.BaseSecurity

class TornadoClient(object):
  def __init__(self, service):
    """ 
      Defining usefull variables
      ==> Should be generated with dirac.cfg
    """
    self.service  = service
    self.port     = 8888
    # 127.0.0.1 in hard in /etc/hosts, should use this url because Tornado check domain name in host certificate and so refuse 'https://localhost'
    self.domain   = 'dirac.cern.ch' 
    self.protocol = 'https'
    self.RPCroot  = '/'

    self.rootUrl = self.protocol+"://"+self.domain+":"+str(self.port)+self.RPCroot

  def __getattr__(self,attrname):
    """ 
      Return the RPC call procedure
    """
    def call(*args):
      return self.RPC(attrname, *args)

    return call

  def RPC(self, procedure, *args):
    """
      This function call a remote service
    """
    # Init the HTTP Client
    http_client = HTTPClient()

    # Write arguments in HTTP headers
    h=HTTPHeaders()
    if args:
      for i in args:
        h.add("args", url_escape(str(i)))



    # Prepare the request
    request = HTTPRequest(
      self.rootUrl+"Service/"+self.service+"/"+procedure,
      headers = h, 
      client_cert = os.path.join('/tmp/', "x509up_u0"),
      ca_certs = os.path.join('/root/dev/etc/grid-security/','hostcert.pem')
    )



    response =  http_client.fetch(request)
    # Return decoded response
    return json_decode(response.body)
