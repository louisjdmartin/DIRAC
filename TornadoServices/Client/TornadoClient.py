import os
import ssl
import httplib
import urllib
import requests
import urlparse
import time

from DIRAC import S_OK
from DIRAC.Core.Utilities.JEncode import encode, decode
from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName, getSystemSection, getServiceURL


class TornadoClient(object):


  VAL_EXTRA_CREDENTIALS_HOST = "hosts"

  KW_USE_CERTIFICATES = "useCertificates"
  KW_EXTRA_CREDENTIALS = "extraCredentials"
  KW_TIMEOUT = "timeout"
  KW_SETUP = "setup"
  KW_VO = "VO"
  KW_DELEGATED_DN = "delegatedDN"
  KW_DELEGATED_GROUP = "delegatedGroup"
  KW_IGNORE_GATEWAYS = "ignoreGateways"
  KW_PROXY_LOCATION = "proxyLocation"
  KW_PROXY_STRING = "proxyString"
  KW_PROXY_CHAIN = "proxyChain"
  KW_SKIP_CA_CHECK = "skipCACheck"
  KW_KEEP_ALIVE_LAPSE = "keepAliveLapse"





  def __init__(self, serviceName, **kwargs):
    """
      :param serviceName: URL of the service (proper uri or just System/Component)
      :param useCertificates: If set to True, use the server certificate
      :param extraCredentials:
      :param timeout: Timeout of the call (default 600 s)
      :param setup: Specify the Setup
      :param VO: Specify the VO
      :param delegatedDN: Not clear what it can be used for.
      :param delegatedGroup: Not clear what it can be used for.
      :param ignoreGateways: Ignore the DIRAC Gatways settings
      :param proxyLocation: Specify the location of the proxy
      :param proxyString: Specify the proxy string
      :param proxyChain: Specify the proxy chain
      :param skipCACheck: Do not check the CA
      :param keepAliveLapse: Duration for keepAliveLapse (heartbeat like)
    """

    if not isinstance(serviceName, basestring):
      raise TypeError("Service name expected to be a string. Received %s type %s" %
                      (str(serviceName), type(serviceName)))

    self.connection = None
    self._destinationSrv = serviceName
    self._serviceName = serviceName
    self.kwargs = kwargs
    self.__useCertificates = None
    # The CS useServerCertificate option can be overridden by explicit argument
    self.__forceUseCertificates = self.kwargs.get(self.KW_USE_CERTIFICATES)
    self.__initStatus = S_OK()
    self.__idDict = {}
    self.__extraCredentials = ""
    self.__retry = 0
    self.__retryDelay = 0
    # by default we always have 1 url for example:
    # RPCClient('dips://volhcb38.cern.ch:9162/Framework/SystemAdministrator')
    self.__nbOfUrls = 1
    self.__nbOfRetry = 3  # by default we try try times
    self.__retryCounter = 1
    self.__bannedUrls = []
    for initFunc in (self._initialize, self.__discoverTimeout):
      """
        self.__discoverVO, self.__discoverTimeout,
        self.__discoverURL, self.__discoverCredentialsToUse,
        self.__checkTransportSanity,
        self.__setKeepAliveLapse
      """
      result = initFunc()
      if not result['OK'] and self.__initStatus['OK']:
        self.__initStatus = result
    self.numberOfURLs = 0
    
    self.__generateSSLContext()

  
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
    self._connect()

    # Start request
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    self.connection.request("POST", self.path, rpcCall, headers)

    # Return result after conversion json->python list
    retVal = decode(self.connection.getresponse().read())[0]

    # Close connection
    self._disconnect()
    return retVal



  def _initialize(self):

    if not self._serviceName.startswith("https"): # Service at format system/service
      url = getServiceURL(self._serviceName)
    else: # Direct URL
      url = self._serviceName
    url_parsed = urlparse.urlparse(url)
    self.path = url_parsed.path
    self.hostname = url_parsed.hostname
    self.port = url_parsed.port
    return S_OK()

  def __discoverTimeout(self):
    """ Discover which timeout to use and stores it in self.timeout
        The timeout can be specified kwargs of the constructor (see KW_TIMEOUT),
        with a minimum of 120 seconds.
        If unspecified, the timeout will be 600 seconds.
        The value is set in self.timeout, as well as in self.kwargs[KW_TIMEOUT]
    """
    if self.KW_TIMEOUT in self.kwargs:
      self.timeout = self.kwargs[self.KW_TIMEOUT]
    else:
      self.timeout = False
    if self.timeout:
      self.timeout = max(120, self.timeout)
    else:
      self.timeout = 600
    self.kwargs[self.KW_TIMEOUT] = self.timeout
    return S_OK()

  def __generateSSLContext(self):
    #### TODO ####
    # Generate context with correct certificates

    # Create SSLContext and load client/CA certificates
    ssl_ctx = ssl.create_default_context()
    #ssl_ctx.load_cert_chain(os.path.join('/tmp/', "x509up_u0"))
    ssl_ctx.load_cert_chain(
        os.path.join(
            '/root/.globus/',
            "usercert.pem"),
        os.path.join(
            '/root/.globus/',
            "userkey.pem"))
    self.ssl_ctx = ssl_ctx


 




  ## These method are here to match with old interface
  def getServiceName(self):
    return self._serviceName

  def getDestinationService(self):
    return getServiceURL(self._serviceName)

  def _connect(self):
    #### TODO ####
    # Same connect as BaseClient
    self.connection = httplib.HTTPSConnection(
        self.hostname,
        port=self.port,
        context=self.ssl_ctx,
        timeout=self.timeout
    )
    self.connection.connect()



  def _disconnect(self):
    self.connection.close()
    self.connection = None


# NOTE pour utilisation requests
# https://lukasa.co.uk/2017/02/Configuring_TLS_With_Requests/
# Depuis requests 2.12 certains chiffrements ne sont plus acceptees
# Passer Tornado en AES ?
