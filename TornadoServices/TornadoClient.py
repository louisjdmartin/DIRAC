from tornado.httputil import HTTPHeaders
from tornado.httpclient import HTTPRequest, HTTPResponse,HTTPClient
import json
import os, ssl
import httplib
import urllib

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
    self.RPCroot  = '/'


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

    # Encode arguments for POST request
    args = urllib.urlencode({'args':json.dumps(args)})

    # Create SSL_CTX and load client/CA certificates
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.load_cert_chain(os.path.join('/tmp/', "x509up_u0"))
    ssl_ctx.load_verify_locations(os.path.join('/root/dev/etc/grid-security/','hostcert.pem'))

    # Create HTTP Connection
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept":"application/json"}
    conn = httplib.HTTPSConnection(
      self.domain, 
      port=self.port, 
      context=ssl_ctx,
    )

    # Start request
    conn.request(
      "POST", 
      self.RPCroot+"Service/"+self.service+"/"+procedure,
      args,
      headers
    )
    
    # Return result after conversion json->python list
    return json.load(conn.getresponse())