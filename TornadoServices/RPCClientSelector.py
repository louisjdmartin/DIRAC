from TornadoClient import TornadoClient
from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC.ConfigurationSystem.Client.PathFinder import divideFullName, getSystemSection
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC import gLogger


# Must be a class later...

def RPCClientSelector(service, setup = None):
  try:
    TornadoServices = gConfigurationData.extractOptionFromCFG("/HTTPServer/Services").replace(" ", "").split(',')
  except AttributeError: # If not defined
    TornadoServices = []
  if(service in TornadoServices): #http ou https
    gLogger.debug("Tornado service found, using TornadoClient.")
    return TornadoClient(service)
  else: #dip ou dips
    gLogger.debug("Tornado service not found, using RPCClient.")
    return RPCClient(service)
