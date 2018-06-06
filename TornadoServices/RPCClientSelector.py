from TornadoClient import TornadoClient
from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC.ConfigurationSystem.Client.PathFinder import getServiceURL
from DIRAC import gLogger
import re



def isCompleteURL(url):
  return re.match(r'^(?:http|dip)s?://', url) is not None


def RPCClientSelector(*args, **kwargs): #We use same interface as RPCClient
  """ Return an RPCClient object 
  """

  # URL can be just "system/service" or "dips://domain:port/system/service"
  # We have to make URL resolution BEFORE the RPCClient or TornadoClient to determine wich one we want to use
  # URL is defined as first argument (called serviceName) in RPCClient
  try:
    serviceName = args[0]
    gLogger.verbose("Trying to autodetect client for %s" % serviceName)
    if not isCompleteURL(serviceName):
      completeUrl = getServiceURL(serviceName) 
      gLogger.verbose("URL resolved: %s" % completeUrl)
    else:
      completeURL = serviceName
    if completeUrl.find("https") == 0:
      gLogger.info("Using HTTPS for service %s" % serviceName)
      rpc = TornadoClient(*args, **kwargs)
    else:
      rpc = RPCClient(*args, **kwargs)
  except Exception as e:
    # If anything wen't wrong in the resolution, we return default RPCClient
    # So the comportement is exactly the same as before implementation of Tornado
    rpc = RPCClient(*args, **kwargs)
  return rpc