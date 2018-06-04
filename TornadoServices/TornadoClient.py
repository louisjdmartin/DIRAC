import os
import ssl
import httplib
import urllib
import requests
import urlparse
import time
from DIRAC.Core.Utilities.JEncode import encode, decode
from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName, getSystemSection, getServiceURL
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData


class TornadoClient(object):
  def __init__(self, service, setup=None, **kwargs):
    """
      Defining useful variables

      :param str service: Name of the service
    """
    self.setup = setup

    
    if service.find("https") != 0: # Service at format system/service
      url = getServiceURL(service)
    else: # Direct URL
      url = service

    url_parsed = urlparse.urlparse(url)
    self.service = service
    self.path = url_parsed.path
    self.hostname = url_parsed.hostname
    self.port = url_parsed.port


    self.__generateSSLContext()


  def __generateSSLContext(self):
    # Create SSLContext and load client/CA certificates
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.load_verify_locations(os.path.join('/root/dev/etc/grid-security/', 'hostcert.pem'))
    ssl_ctx.load_cert_chain(os.path.join('/tmp/', "x509up_u0"))
    #ssl_ctx.load_cert_chain(
    #    os.path.join(
    #        '/root/.globus/',
    #        "usercert.pem"),
    #    os.path.join(
    #        '/root/.globus/',
    #        "userkey.pem"))
    self.ssl_ctx = ssl_ctx

  def __getattr__(self, attrname):
    """
      Return the RPC call procedure
      :param str attrname: Name of the procedure we are trying to call
      :return: RPC procedure
    """
    def call(*args):
      return self.executeRPC(attrname, *args)
    return call


  def executeRPC(self, method, *args):
    """
      This function call a remote service
      :param str procedure: remote procedure name
      :param args: list of arguments
      :return: decoded response from server, server may return S_OK or S_ERROR
    """

    rpcCall = urllib.urlencode({'method': method, 'args': encode(args)})

    # Create HTTP Connection
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}

    conn = httplib.HTTPSConnection(
        self.hostname,
        port=self.port,
        context=self.ssl_ctx,
    )

    # Start request
    conn.request(
        "POST",
        self.path,
        rpcCall,
        headers
    )
    # Return result after conversion json->python list
    retVal = decode(conn.getresponse().read())[0]
    return retVal



  ## These method are here to match with old interface
  def getServiceName(self):
    return self.service
  def getDestinationService(self):
    return getServiceURL(self.service)





  def doRPC1(self, procedure, *args):
    """
      This function call a remote service
      :param str procedure: remote procedure name
      :param args: list of arguments
      :return: decoded response from server, server may return S_OK or S_ERROR
    """
    # Encode arguments for POST request
    args = {'args': json.dumps(args)}
    response = requests.post(
        self.path, ## URL INCORRECTE !
        # cert=('/root/.globus/usercert.pem', '/root/.globus/userkey.pem'), #Fonctionne
        cert=('/tmp/x509up_u0', '/tmp/x509up_u0'),  # Fonctionne pas
        verify=False,
        data=args
    )

    return response.json()

# NOTE
# https://lukasa.co.uk/2017/02/Configuring_TLS_With_Requests/
# Depuis requests 2.12 certains chiffrements ne sont plus acceptees
# Passer Tornado en AES ?
