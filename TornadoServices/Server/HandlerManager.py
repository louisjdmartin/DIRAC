# TODO: Remove some import...

from os.path import realpath
from DIRAC.Core.Utilities.ObjectLoader import ObjectLoader
from tornado.web import url as TornadoURL, RequestHandler
from DIRAC import gLogger, S_ERROR, S_OK, gConfig
from types import ModuleType
import DIRAC
from DIRAC.ConfigurationSystem.Client.Helpers import CSGlobals
from DIRAC.Core.Base.private.ModuleLoader import ModuleLoader
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName
from DIRAC.ConfigurationSystem.Client.PathFinder import getServiceURL


class HandlerManager(object):
  """
    This class is designed to work with Tornado
    handlers are stored in tornado.web.url object so they are ready to use
    in Tornado (tornado.web.url store the handler and rooting informations)
  """

  def __init__(self, autoDiscovery=True, setup=None):
    """
      Initialization function, you can set autoDiscovery=False to prevent automatic
      discovery of handler. If disabled you can use loadHandlersByServiceName() to 
      load your handlers or loadHandlerInHandlerManager()
    """
    self.__handlers = {}
    self.__objectLoader = ObjectLoader()
    self.setup = setup
    self.__autoDiscovery = autoDiscovery
    self.loader = ModuleLoader("Service", PathFinder.getServiceSection, RequestHandler, moduleSuffix="Handler")

  def __addHandler(self, handlerTuple, url=None):
    """
      Function who add handler to list of known handlers


      :param handlerTuple: (path, class) --> ObjectLoader.getObjects() returns in this form, it's why we use it like this
    """
    # Check if handler not already loaded
    if not url or url not in self.__handlers:
      gLogger.debug("Find new handler %s" % (handlerTuple[0]))

      # If url is not given, try to discover it
      if url is None:
        # FIRST TRY: Url is hardcoded
        try:
          url = handlerTuple[1].LOCATION
        # SECOND TRY: URL can be deduced from path
        except AttributeError:
          gLogger.debug("No location defined for %s try to get it from path" % handlerTuple[0])
          url = self.__urlFinder(handlerTuple[0])

      # We add "/" if missing at begin, e.g. we found "Framework/Service"
      # URL can't be relative in Tornado
      if url and not url.find('/') == 0:
        url = "/%s" % url
      elif not url:
        gLogger.warn("URL not found for %s" % (handlerTuple[0]))
        return S_ERROR("URL not found for %s" % (handlerTuple[0]))

      # Finally add the URL to handlers
      if not url in self.__handlers:
        self.__handlers[url] = handlerTuple[1]
        gLogger.info("New handler: %s with URL %s" % (handlerTuple[0], url))
    else:
      gLogger.debug("Handler already loaded %s" % (handlerTuple[0]))
    return S_OK

  def discoverHandlers(self):
    """
      Force the discovery of URL, automatic call when we try to get handlers for the first time.
      You can disable the automatic call with autoDiscovery=False at initialization 
    """
    gLogger.debug("Trying to auto-discover the handlers for Tornado")

    # Look in config file
    diracSystems = gConfig.getSections('/Systems')
    serviceList = []
    if diracSystems['OK']:
      for system in diracSystems['Value']:
        instance = PathFinder.getSystemInstance(system)
        services = gConfig.getSections('/Systems/%s/%s/Services' % (system, instance))
        if services['OK']:
          for service in services['Value']:
            newservice = ("%s/%s" % (system, service))
            newserviceurl = getServiceURL(newservice) 
            if newserviceurl.startswith('http'):
              serviceList.append(newservice)

    self.loadHandlersByServiceName(serviceList)


  def loadHandlersByServiceName(self, servicesNames):
    """
      Load a list of handler from list of service using DIRAC moduleLoader
      Use :py:class:`DIRAC.Core.Base.private.ModuleLoader`

      :param servicesNames: list of service, e.g. ['Framework/Hello', 'Configuration/ConfigurationTornado']
    """

    # Use DIRAC system to load: search in CS if path is given and if not defined
    # it search in place it should be (e.g. in DIRAC/FrameworkSystem/Service)
    if not isinstance(servicesNames, list):
      servicesNames = [servicesNames]

    load = self.loader.loadModules(servicesNames)
    if load['OK']:
      for module in self.loader.getModules().values():
        url = getServiceURL(module['loadName']) 
        serviceTuple = url.replace('https://', '').split('/')[-2:]
        url = "%s/%s" % (serviceTuple[0], serviceTuple[1])
        self.__addHandler((module['loadName'], module['classObj']), url)
      return S_OK()
    return load

  def __urlFinder(self, module):
    """
      Try to guess the url with module name

      :param module: path writed like import (e.g. "DIRAC.something.something")
    """
    sections = module.split('.')
    for section in sections:
      # This condition is a bit long
      # We search something who look like <...>.<component>System.<...>.<service>Handler
      # If find we return /<component>/<service>
      if(section.find("System") > 0) and (sections[-1].find('Handler') > 0):
        return "/%s/%s" % (section.replace("System", ""), sections[-1].replace("Handler", ""))
    return None

  def getHandlersURLs(self):
    """
      Get all handler for usage in Tornado, as a list of tornado.web.url
      If there is no handler found before, it try to find them
    """
    if self.__handlers == {} and self.__autoDiscovery:
      self.__autoDiscovery = False
      self.discoverHandlers()
    urls = []  
    for key in handlerDict.keys():
      urls.append(TornadoURL(key, handlerDict[key]))
    return urls

  def getHandlersDict(self):
    """
      Return all handler dictionnary
      - Keys: URL at str format, e.g.: "/Framework/Service"
      - Values: tornado.web.url, ready to use in tornado
    """
    if self.__handlers == {} and self.__autoDiscovery:
      self.__autoDiscovery = False
      self.discoverHandlers()
    return self.__handlers
