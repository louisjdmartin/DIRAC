import json
import os, ssl
import httplib
import urllib
import requests

class TornadoClient(object):
  def __init__(self, service):
    """ 
      Defining useful variables
      ==> Should be generated with dirac.cfg
      :param str service: Name of the service
    """
    self.service  = service
    self.port     = 8888
    # 127.0.0.1 in hard in /etc/hosts, should use this url because SSL  check domain name in host certificate and so refuse 'https://localhost'
    # ssl.CertificateError: hostname 'localhost' doesn't match u'dirac.cern.ch'
    self.domain   = 'dirac.cern.ch' 
    self.RPCrootURL  = '/Service/'


  def __getattr__(self,attrname):
    """ 
      Return the RPC call procedure
      :param str attrname: Name of the procedure we are trying to call
      :return: RPC procedure
    """
    def call(*args):
      return self.doRPC(attrname, *args)

    return call

  def doRPC(self, procedure, *args):
    """
      This function call a remote service
      :param str procedure: remote procedure name
      :param args: list of arguments
      :return: decoded response from server, server may return S_OK or S_ERROR
    """
    args = urllib.urlencode({'args':json.dumps(args)})

    # Create SSLContext and load client/CA certificates
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
      self.RPCrootURL+self.service+"/"+procedure,
      args,
      headers
    )
    
    # Return result after conversion json->python list
    return json.load(conn.getresponse())
    
  def doRPC1(self, procedure, *args):
    """
      This function call a remote service
      :param str procedure: remote procedure name
      :param args: list of arguments
      :return: decoded response from server, server may return S_OK or S_ERROR
    """
    # Encode arguments for POST request
    args ={'args':json.dumps(args)}
    response = requests.post(
      'https://%s:%d%s%s/%s' % (self.domain, self.port, self.RPCrootURL, self.service, procedure),
      #cert=('/root/.globus/usercert.pem', '/root/.globus/userkey.pem'), #Fonctionne
      cert=('/tmp/x509up_u0', '/tmp/x509up_u0'), #Fonctionne pas
      verify=False,
      data=args
    )
    return response.json()
    
## NOTE
## https://lukasa.co.uk/2017/02/Configuring_TLS_With_Requests/
## Depuis requests 2.12 certains chiffrements ne sont plus acceptees
## Passer Tornado en AES ?