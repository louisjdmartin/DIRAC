import os
import ssl
import httplib
import urllib
import requests
import urlparse
import time

import DIRAC
from DIRAC import S_OK, gLogger
from DIRAC.Core.Utilities.JEncode import encode, decode
from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName, getSystemSection, getServiceURL
from DIRAC.TornadoServices.Client.private.Protocols import gProtocolList
from DIRAC.ConfigurationSystem.Client.Config import gConfig
from DIRAC.Core.Utilities import List, Network


class TornadoClient(object):
  """
    Client for calling tornado services
    Most of the method are based from DIRAC.Core.DISET.private.BaseClient
    and adapted for HTTPS and Tornado
  """



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
    for initFunc in (self.__discoverTimeout, self.__discoverSetup, self.__discoverVO):
      """
        self.__discoverVO, self.__discoverTimeout,
        self.__discoverURL, self.__discoverCredentialsToUse,
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




  def __discoverSetup(self):
    """ Discover which setup to use and stores it in self.setup
        The setup is looked for:
           * kwargs of the constructor (see KW_SETUP)
           * the ThreadConfig
           * in the CS /DIRAC/Setup
           * default to 'Test'
    """
    if self.KW_SETUP in self.kwargs and self.kwargs[self.KW_SETUP]:
      self.setup = str(self.kwargs[self.KW_SETUP])
    else:
      self.setup = gConfig.getValue("/DIRAC/Setup", "Test")
    return S_OK()

  def __discoverURL(self):
    """ Calculate the final URL. It is called at initialization and in connect in case of issue

        It sets:
          * self.serviceURL: the url (dips) selected as target using __findServiceURL
          * self.__URLTuple: a split of serviceURL obtained by Network.splitURL
          * self._serviceName: the last part of URLTuple (typically System/Component)
    """
    # Calculate final URL
    try:
      result = self.__findServiceURL()
    except Exception as e:
      return S_ERROR(repr(e))
    if not result['OK']:
      return result
    self.serviceURL = result['Value']
    retVal = Network.splitURL(self.serviceURL)
    if not retVal['OK']:
      return retVal
    self.__URLTuple = retVal['Value']
    self._serviceName = self.__URLTuple[-1]
    res = gConfig.getOptionsDict("/DIRAC/ConnConf/%s:%s" % self.__URLTuple[1:3])
    if res['OK']:
      opts = res['Value']
      for k in opts:
        if k not in self.kwargs:
          self.kwargs[k] = opts[k]
    return S_OK()

  def __discoverVO(self):
    """ Discover which VO to use and stores it in self.vo
        The VO is looked for:
           * kwargs of the constructor (see KW_VO)
           * in the CS /DIRAC/VirtualOrganization
           * default to 'unknown'
    """
    if self.KW_VO in self.kwargs and self.kwargs[self.KW_VO]:
      self.vo = str(self.kwargs[self.KW_VO])
    else:
      self.vo = gConfig.getValue("/DIRAC/VirtualOrganization", "unknown")
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



  def __findServiceURL(self):
    """
        Discovers the URL of a service, taking into account gateways, multiple URLs, banned URLs


        If the site on which we run is configured to use gateways (/DIRAC/Gateways/<siteName>),
        these URLs will be used. To ignore the gateway, it is possible to set KW_IGNORE_GATEWAYS
        to False in kwargs.

        If self._destinationSrv (given as constructor attribute) is a properly formed URL,
        we just return this one. If we have to use a gateway, we just replace the server name in the url.

        The list of URLs defined in the CS (<System>/URLs/<Component>) is randomized

        This method also sets some attributes:
          * self.__nbOfUrls = number of URLs
          * self.__nbOfRetry = 2 if we have more than 2 urls, otherwise 3
          * self.__bannedUrls is reinitialized if all the URLs are banned

        :return: the selected URL

    """
    if not self.__initStatus['OK']:
      return self.__initStatus

    # Load the Gateways URLs for the current site Name
    gatewayURL = False
    if self.KW_IGNORE_GATEWAYS not in self.kwargs or not self.kwargs[self.KW_IGNORE_GATEWAYS]:
      dRetVal = gConfig.getOption("/DIRAC/Gateways/%s" % DIRAC.siteName())
      if dRetVal['OK']:
        rawGatewayURL = List.randomize(List.fromChar(dRetVal['Value'], ","))[0]
        gatewayURL = "/".join(rawGatewayURL.split("/")[:3])

    # If what was given as constructor attribute is a properly formed URL,
    # we just return this one.
    # If we have to use a gateway, we just replace the server name in it
    for protocol in gProtocolList:
      if self._destinationSrv.find("%s://" % protocol) == 0:
        gLogger.debug("Already given a valid url", self._destinationSrv)
        if not gatewayURL:
          return S_OK(self._destinationSrv)
        gLogger.debug("Reconstructing given URL to pass through gateway")
        path = "/".join(self._destinationSrv.split("/")[3:])
        finalURL = "%s/%s" % (gatewayURL, path)
        gLogger.debug("Gateway URL conversion:\n %s -> %s" % (self._destinationSrv, finalURL))
        return S_OK(finalURL)

    if gatewayURL:
      gLogger.debug("Using gateway", gatewayURL)
      return S_OK("%s/%s" % (gatewayURL, self._destinationSrv))

    # We extract the list of URLs from the CS (System/URLs/Component)
    try:
      urls = getServiceURL(self._destinationSrv, setup=self.setup)
    except Exception as e:
      return S_ERROR("Cannot get URL for %s in setup %s: %s" % (self._destinationSrv, self.setup, repr(e)))
    if not urls:
      return S_ERROR("URL for service %s not found" % self._destinationSrv)

    failoverUrls = []
    # Try if there are some failover URLs to use as last resort
    try:
      failoverUrlsStr = getServiceFailoverURL(self._destinationSrv, setup=self.setup)
      if failoverUrlsStr:
        failoverUrls = failoverUrlsStr.split(',')
    except Exception as e:
      pass

    # We randomize the list, and add at the end the failover URLs (System/FailoverURLs/Component)
    urlsList = List.randomize(List.fromChar(urls, ",")) + failoverUrls
    self.__nbOfUrls = len(urlsList)
    self.__nbOfRetry = 2 if self.__nbOfUrls > 2 else 3  # we retry 2 times all services, if we run more than 2 services
    if self.__nbOfUrls == len(self.__bannedUrls):
      self.__bannedUrls = []  # retry all urls
      gLogger.debug("Retrying again all URLs")

    if len(self.__bannedUrls) > 0 and len(urlsList) > 1:
      # we have host which is not accessible. We remove that host from the list.
      # We only remove if we have more than one instance
      for i in self.__bannedUrls:
        gLogger.debug("Removing banned URL", "%s" % i)
        urlsList.remove(i)

    # Take the first URL from the list
    #randUrls = List.randomize( urlsList ) + failoverUrls

    sURL = urlsList[0]

    # If we have banned URLs, and several URLs at disposals, we make sure that the selected sURL
    # is not on a host which is banned. If it is, we take the next one in the list using __selectUrl
    # If we have banned URLs, and several URLs at disposals, we make sure that the selected sURL
    # is not on a host which is banned. If it is, we take the next one in the list using __selectUrl

    if len(self.__bannedUrls) > 0 and self.__nbOfUrls > 2:  # when we have multiple services then we can
      # have a situation when two services are running on the same machine with different ports...
      retVal = Network.splitURL(sURL)
      nexturl = None
      if retVal['OK']:
        nexturl = retVal['Value']

        found = False
        for i in self.__bannedUrls:
          retVal = Network.splitURL(i)
          if retVal['OK']:
            bannedurl = retVal['Value']
          else:
            break
          # We found a banned URL on the same host as the one we are running on
          if nexturl[1] == bannedurl[1]:
            found = True
            break
        if found:
          nexturl = self.__selectUrl(nexturl, urlsList[1:])
          if nexturl:  # an url found which is in different host
            sURL = nexturl
    gLogger.debug("Discovering URL for service", "%s -> %s" % (self._destinationSrv, sURL))
    return S_OK(sURL)



  def __generateSSLContext(self):
    """#### TODO ####
    # Generate context with correct certificates
    # Create SSLContext and load client/CA certificates"""
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
    # _connect like BaseClient._connect
    url = self.__findServiceURL()
    if not url['OK']:
      return url
    url_parsed = urlparse.urlparse(url['Value'])
    self.path = url_parsed.path
    self.hostname = url_parsed.hostname
    self.port = url_parsed.port
    self.connection = httplib.HTTPSConnection(
        self.hostname,
        port=self.port,
        context=self.ssl_ctx,
        timeout=self.timeout
    )
    self.connection.connect()
    return S_OK()


  def _disconnect(self):
    self.connection.close()
    self.connection = None


# NOTE pour utilisation requests
# https://lukasa.co.uk/2017/02/Configuring_TLS_With_Requests/
# Depuis requests 2.12 certains chiffrements ne sont plus acceptees
# Passer Tornado en AES ?
