"""
    TornadoBaseClient contain all low-levels functionnalities and initilization methods
    It must be instanciated from a child class like TornadoClient

    Requests library manage himself retry when connection failed, so the number of "retry" in this class is equal
    to the number of URL. (For each URL requests manage retry himself, if it still fail, we try next url)
    KeepAlive lapse is also removed because managed by request, see http://docs.python-requests.org/en/master/user/advanced/#keep-alive

    If necessary this class can be modified to define number of retry in requestspytest, documentation does not give lot of informations
    but you can see this simple solution from StackOverflow. After some tests request seems to retry 3 times.
    https://stackoverflow.com/questions/15431044/can-i-set-max-retries-for-requests-request

    WARNING: If you use your own certificates please take a look at
    https://dirac.readthedocs.io/en/latest/AdministratorGuide/InstallingDIRACService/index.html#using-your-own-ca


"""
import requests
import DIRAC

from DIRAC.ConfigurationSystem.Client.Config import gConfig
from DIRAC.Core.Utilities import List, Network
from DIRAC import S_OK, S_ERROR, gLogger
from DIRAC.ConfigurationSystem.Client.PathFinder import getServiceURL, getServiceFailoverURL
from DIRAC.Core.Utilities.JEncode import decode, encode
from DIRAC.Core.Security import CS
from DIRAC.Core.Security import Locations


class TornadoBaseClient(object):
  """
    This class contain initialization method and all utilities method used for RPC
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

    # TODO: redefine and use this
    self._destinationSrv = serviceName
    self._serviceName = serviceName
    self.__ca_location = False

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
    #self.__nbOfRetry removed in https, see note at the begining of the class
    self.__retryCounter = 1
    self.__bannedUrls = []
    for initFunc in (
        self.__discoverTimeout,
        self.__discoverSetup,
        self.__discoverVO,
        self.__discoverCredentialsToUse,
        self.__discoverExtraCredentials,
        self.__discoverURL):
      """
        self.__setKeepAliveLapse
      """
      result = initFunc()
      if not result['OK'] and self.__initStatus['OK']:
        self.__initStatus = result
    self.numberOfURLs = 0

  def __discoverSetup(self):
    """ Discover which setup to use and stores it in self.setup
        The setup is looked for:
           * kwargs of the constructor (see KW_SETUP)
           * in the CS /DIRAC/Setup
           * default to 'Test'

        WARNING: COPY/PASTE FROM Core/Diset/private/BaseClient FOR NOW
        Except a line who get value from threadconfig
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

      WARNING: COPY PASTE FROM BaseClient
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

        WARNING: COPY/PASTE FROM Core/Diset/private/BaseClient FOR NOW
        Used in propose action, but not reused
        # TODO: See how it's sended and why
    """
    if self.KW_VO in self.kwargs and self.kwargs[self.KW_VO]:
      self.vo = str(self.kwargs[self.KW_VO])
    else:
      self.vo = gConfig.getValue("/DIRAC/VirtualOrganization", "unknown")
    return S_OK()

  def __discoverCredentialsToUse(self):
    """ Discovers which credentials to use for connection.
        * Server certificate:
          -> If KW_USE_CERTIFICATES in kwargs, sets it in self.__useCertificates
          -> If not, check gConfig.useServerCertificate(), and sets it in self.__useCertificates 
              and kwargs[KW_USE_CERTIFICATES]
        * Certification Authorities check:
           -> if KW_SKIP_CA_CHECK is not in kwargs and we are using the certificates, 
                set KW_SKIP_CA_CHECK to false in kwargs
           -> if KW_SKIP_CA_CHECK is not in kwargs and we are not using the certificate, check the CS.skipCACheck
        * Proxy Chain

        WARNING: MOSTLY COPY/PASTE FROM Core/Diset/private/BaseClient

    """
    # Use certificates?
    if self.KW_USE_CERTIFICATES in self.kwargs:
      self.__useCertificates = self.kwargs[self.KW_USE_CERTIFICATES]
    else:
      self.__useCertificates = gConfig.useServerCertificate()
      self.kwargs[self.KW_USE_CERTIFICATES] = self.__useCertificates
    if self.KW_SKIP_CA_CHECK not in self.kwargs:
      if self.__useCertificates:
        self.kwargs[self.KW_SKIP_CA_CHECK] = False
      else:
        self.kwargs[self.KW_SKIP_CA_CHECK] = CS.skipCACheck()
    if self.KW_PROXY_CHAIN in self.kwargs:
      try:
        self.kwargs[self.KW_PROXY_STRING] = self.kwargs[self.KW_PROXY_CHAIN].dumpAllToString()['Value']
        del self.kwargs[self.KW_PROXY_CHAIN]
      except BaseException:
        return S_ERROR("Invalid proxy chain specified on instantiation")

    ##### REWRITED FROM HERE #####

    # Getting proxy
    
    proxy = Locations.getProxyLocation()
    if not proxy:
      gLogger.error("No proxy found")
      return S_ERROR("No proxy found")
    self.__proxy_location = proxy

    # For certs always check CA's. For clients skipServerIdentityCheck
    if self.KW_SKIP_CA_CHECK not in self.kwargs or not self.kwargs[self.KW_SKIP_CA_CHECK]:
      cafile = Locations.getCAsLocation()
      if not cafile:
        gLogger.error("No CAs found!")
        return S_ERROR("No CAs found!")
      else:
        self.__ca_location = cafile

    return S_OK()

  def __discoverExtraCredentials(self):
    """ Add extra credentials informations.
        * self.__extraCredentials
          -> if KW_EXTRA_CREDENTIALS in kwargs, we set it
          -> Otherwise, if we use the server certificate, we set it to VAL_EXTRA_CREDENTIALS_HOST
          -> If we have a delegation (see bellow), we set it to (delegatedDN, delegatedGroup)
          -> otherwise it is an empty string
        * delegation:
          -> if KW_DELEGATED_DN in kwargs, or delegatedDN in threadConfig, put in in self.kwargs
          -> If we have a delegated DN but not group, we find the corresponding group in the CS

    WARNING: (mostly) COPY/PASTE FROM Core/Diset/private/BaseClient
    -> Interactions with thread removed
    """
    # Wich extra credentials to use?
    if self.__useCertificates:
      self.__extraCredentials = self.VAL_EXTRA_CREDENTIALS_HOST
    else:
      self.__extraCredentials = ""
    if self.KW_EXTRA_CREDENTIALS in self.kwargs:
      self.__extraCredentials = self.kwargs[self.KW_EXTRA_CREDENTIALS]
    # Are we delegating something?
    if self.KW_DELEGATED_DN in self.kwargs and self.kwargs[self.KW_DELEGATED_DN]:
      delegatedDN = self.kwargs[self.KW_DELEGATED_DN]
    else:
      delegatedDN=False
    if self.KW_DELEGATED_GROUP in self.kwargs and self.kwargs[self.KW_DELEGATED_GROUP]:
      delegatedGroup = self.kwargs[self.KW_DELEGATED_GROUP]
    else:
      delegatedGroup=False
    if delegatedDN:
      if not delegatedGroup:
        result = CS.findDefaultGroupForDN(self.kwargs[self.KW_DELEGATED_DN])
        if not result['OK']:
          return result
      self.__extraCredentials = (delegatedDN, delegatedGroup)

      print self.__extraCredentials
    return S_OK()

  def __discoverTimeout(self):
    """ Discover which timeout to use and stores it in self.timeout
        The timeout can be specified kwargs of the constructor (see KW_TIMEOUT),
        with a minimum of 120 seconds.
        If unspecified, the timeout will be 600 seconds.
        The value is set in self.timeout, as well as in self.kwargs[KW_TIMEOUT]

        WARNING: COPY/PASTE FROM Core/Diset/private/BaseClient
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
          * self.__nbOfRetry removed in HTTPS (Managed by requests)
          * self.__bannedUrls is reinitialized if all the URLs are banned

        :return: the selected URL

        WARNING (Mostly) COPY PASTE FROM BaseClient (protocols list is changed to https)

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
    if self._destinationSrv.find("https://") == 0:
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

    # If nor url is given as constructor, we extract the list of URLs from the CS (System/URLs/Component)
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
    ## __nbOfRetry removed in HTTPS (managed by requests)
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

    if len(self.__bannedUrls) > 0 and self.__nbOfUrls > 2:
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

  def __selectUrl(self, notselect, urls):
    """In case when multiple services are running in the same host, a new url has to be in a different host
    Note: If we do not have different host we will use the selected url...

    :param notselect: URL that should NOT be selected
    :param urls: list of potential URLs

    :return: selected URL

    WARNING: COPY/PASTE FROM Core/Diset/private/BaseClient
    """
    url = None
    for i in urls:
      retVal = Network.splitURL(i)
      if retVal['OK']:
        if retVal['Value'][1] != notselect[1]:  # the hots are different
          url = i
          break
        else:
          gLogger.error(retVal['Message'])
    return url

  def getServiceName(self):
    return self._serviceName

  def getDestinationService(self):
    return getServiceURL(self._serviceName)

  def _getBaseStub(self):
    """ Returns a tuple with (self._destinationSrv, newKwargs)
        self._destinationSrv is what was given as first parameter of the init serviceName

        newKwargs is an updated copy of kwargs:
          * if set, we remove the useCertificates (KW_USE_CERTIFICATES) in newKwargs

        This method is just used to return information in case of error in the InnerRPCClient

        WARNING: COPY/PASTE FROM Core/Diset/private/BaseClient
    """
    newKwargs = dict(self.kwargs)
    # Remove useCertificates as the forwarder of the call will have to
    # independently decide whether to use their cert or not anyway.
    if 'useCertificates' in newKwargs:
      del newKwargs['useCertificates']
    return (self._destinationSrv, newKwargs)

  def _request(self, postArguments, retry=0):

    # Adding some informations to send
    if self.__extraCredentials:
      postArguments[self.KW_EXTRA_CREDENTIALS] = encode(self.__extraCredentials)
    postArguments["clientVO"] = self.vo

    # Getting URL
    url = self.__findServiceURL()
    if not url['OK']:
      return url
    url = url['Value']

    # Getting CA file (or skip verification)
    verify = (not self.kwargs[self.KW_SKIP_CA_CHECK])
    if verify and self.__ca_location:
      verify = self.__ca_location

    # getting certificate
    if self.kwargs[self.KW_USE_CERTIFICATES]:
      cert = Locations.getHostCertificateAndKeyLocation()
    else:
      cert = self.__proxy_location

    print "==================================================="
    print "Certificat client: \t%s\nCA: \t\t\t%s"%(cert, verify)
    print "==================================================="
    print postArguments
    # Do the request
    try:
      call = requests.post(url, data=postArguments, timeout=self.timeout, verify=verify,
                        cert=cert)
      return decode(call.text)[0]
    except Exception as e:
      if url not in self.__bannedUrls:
        self.__bannedUrls += [url]
      if retry < self.__nbOfUrls - 1:
        self._request(postArguments, retry + 1)
      return S_ERROR(e)

#### TODO ####
# Rewrite this method:
#  /Core/DISET/private/BaseClient.py
# __delegateCredentials
