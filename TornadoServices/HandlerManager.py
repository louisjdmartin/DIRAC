from os.path import realpath
from DIRAC.Core.Utilities.ObjectLoader import ObjectLoader
from TornadoService import TornadoService
from tornado.web import url as TornadoURL, RequestHandler
from DIRAC import gLogger, S_ERROR, S_OK, gConfig
from types import ModuleType
import DIRAC
from DIRAC.ConfigurationSystem.Client.Helpers import CSGlobals
from DIRAC.Core.Base.private.ModuleLoader import ModuleLoader
from DIRAC.ConfigurationSystem.Client import PathFinder

from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName
class HandlerManager(object):
  """
    This class is designed to work with Tornado
    handlers are stored in tornado.web.url object so they are ready to use
    in Tornado (tornado.web.url store the handler and rooting informations)
  """

  def __init__(self, autoDiscovery=True, setup=None):
    self.__handlers = {} 
    self.__objectLoader = ObjectLoader()
    self.setup = setup
    self.__autoDiscovery = autoDiscovery
    self.loader = ModuleLoader( "Service",PathFinder.getServiceSection,RequestHandler, moduleSuffix = "Handler" )



  def __addHandler(self, handlerTuple, url=None):
    """
      Function who add handler to list of known handlers


      :param handlerTuple: (path, class) --> ObjectLoader.getObjects() returns in this form, it's why we use it like this
    """
    #Check if handler not already loaded
    if not url or not url in self.__handlers:
      gLogger.debug("Find new handler %s"%(handlerTuple[0]))

      #If url is not given, try to discover it
      if url == None:
        #FIRST TRY: Url is hardcoded
        try:
          url = handlerTuple[1].LOCATION
          if(url.find('/') == 0):
            url = url[1:]
        #SECOND TRY: URL can be deduced from path
        except AttributeError:
          gLogger.debug("No location defined for %s try to get it from path" % handlerTuple[0])
          url = self.__urlFinder(handlerTuple[0])
        

      # We add "/" if missing at begin, e.g. we found "Framework/Service"
      # URL can't be relative in Tornado
      if url and not url.find('/') == 0:
        url = "/%s" % url
      elif not url:
        gLogger.warn("URL not found for %s"%(handlerTuple[0]))
        return S_ERROR("URL not found for %s"%(handlerTuple[0]))

      #Finally add the URL to handlers
      self.__handlers[url] = TornadoURL(url, handlerTuple[1])
      gLogger.info("New handler: %s with URL %s"%(handlerTuple[0], url))
    else:
      gLogger.debug("Handler already loaded %s"%(handlerTuple[0]))
    return S_OK


  def discoverHandlers(self):
    """
      Force the discovery of URL, automatic call when we try to get handlers for the first time.
      You can disable the automatic call with autoDiscovery=False at initialization and use searchHandlers
    """
    gLogger.debug("Trying to discover the handlers for Tornado")

    #Look in tornado
    self.searchHandlers("DIRAC.TornadoServices.Service", recurse=True)

    #Look in extensions
    for extName in CSGlobals.getCSExtensions():
      if extName.rfind( "DIRAC" ) != len( extName ) - 5:
        extName = "%sDIRAC" % extName
      self.searchHandlers(extName, recurse=True)

    #Look in config file
    diracSystems = gConfig.getSections('/Systems')
    serviceList = []
    if diracSystems['OK']:
      for system in diracSystems['Value']:
        instance = PathFinder.getSystemInstance(system)
        services = gConfig.getSections('/Systems/%s/%s/Services'% (system, instance))
        if services['OK']:
          for service in services['Value']:
            serviceList.append("%s/%s" % (system, service))
    self.loadHandlersByServiceName(serviceList)



  def loadHandlerInHandlerManager(self, path, url=None):
    """
      Manually import a handler with name

      :param str path: Something like DIRAC.Component.ServiceHandler
    """
    handler = self.__objectLoader.loadObject(path)
    if handler['OK']:
      self.__addHandler((path, handler['Value']), url)
      return S_OK()
    return S_ERROR()

  def loadHandlersByServiceName(self, servicesNames):
    """
      Load a list of handler from list of service using DIRAC moduleLoader

      :param servicesNames: list of service, e.g. ['Framework/Hello', 'Configuration/ConfigurationTornado']
    """


    # Use DIRAC system to load: search in CS if path is given and if not defined 
    # it search in place it should be (e.g. in DIRAC/FrameworkSystem/Service)
    self.loader.loadModules(servicesNames, hideExceptions=True)['OK']
    for module in self.loader.getModules().values():
      self.__addHandler((module['loadName'],module['classObj']), module['modName'])

  def searchHandlers(self, module, reFilter = "", recurse=False):
    """
      Search handlers in a module.
      You can use this function to force the HandlerManager to search in specific place

      :param str module: Module you want to search
      :param str reFilter: regex expression to filter by name
      :param bool recurse: Recursive search
    """
    handlers = self.__objectLoader.getObjects(module, parentClass=RequestHandler, recurse=recurse, reFilter=reFilter)
    if handlers["OK"] and len(handlers["Value"])>0:
      for handler in handlers['Value'].items():
        self.__addHandler(handler)
      return S_OK()
    return S_ERROR()

        

  def __urlFinder(self, module):
    """
      Try to guess the url with module name
    """
    sections = module.split('.')
    for section in sections:
      # This condition is a bit long
      # We search something who look like <...>.<component>System.<...>.<service>Handler
      # If find we return /<component>/<service>
      if(section.find("System")>0) and (sections[-1].find('Handler')>0):
        return "/%s/%s"%(section.replace("System",""), sections[-1].replace("Handler", ""))
    return None


  def getHandlersURLs(self):
    """
      Get all handler for usage in Tornado, as a list of tornado.web.url 
      If there is no handler found before, it try to find them
    """
    if self.__handlers == {} and self.__autoDiscovery:
      self.__autoDiscovery = False
      self.discoverHandlers()
    return self.__handlers.values()

  def getHandlersDict(self):
    return self.__handlers
