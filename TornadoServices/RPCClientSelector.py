from TornadoClient import TornadoClient
from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName, getSystemSection
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC import gLogger

def RPCClientSelector(service, setup = None):
  serviceTuple = divideFullName( service )
  systemSection = getSystemSection( service, serviceTuple, setup = setup )
  url = gConfigurationData.extractOptionFromCFG( "%s/URLs/%s" % ( systemSection, serviceTuple[1] ) )
  gLogger.debug("Try to get client for URL: %s." % url)
  if(url[:3] == "dip"): #dip ou dips
    gLogger.debug("Find: diset client.")
    return RPCClient(service)
  elif(url[:4] == "http"): #http ou https
    gLogger.debug("Find: tornado client.")
    return TornadoClient(service)
  else:
    gLogger.debug("Fail to find the client.")
    return None