"""
  RPCClientSelector can replace RPCClient (with import RPCClientSelector as RPCClient)
  to migrate from DISET to Tornado. This method chooses and returns the client wich should be
  used for a service. If the service use HTTPS, TornadoClient is returned, else it returns RPCClient

  Example::

    from DIRAC.TornadoServices.Client.RPCClientSelector import RPCClientSelector as RPCClient
    myService = RPCClient("Framework/MyService")
    myService.doSomething()
"""

import re

from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient
from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC.ConfigurationSystem.Client.PathFinder import getServiceURL
from DIRAC import gLogger


def isCompleteURL(url):
  return url.startswith('http') or url.startswith('dip')


def RPCClientSelector(*args, **kwargs):  # We use same interface as RPCClient
  """ 
    Select the correct RPCClient, instanciate it, and return it
    :param args[0]: url: URL can be just "system/service" or "dips://domain:port/system/service"
  """

  # We have to make URL resolution BEFORE the RPCClient or TornadoClient to determine wich one we want to use
  # URL is defined as first argument (called serviceName) in RPCClient
  try:
    serviceName = args[0]
    gLogger.verbose("Trying to autodetect client for %s" % serviceName)
    if not isCompleteURL(serviceName):
      completeUrl = getServiceURL(serviceName)
      gLogger.verbose("URL resolved: %s" % completeUrl)
    else:
      completeUrl = serviceName
    if completeUrl.startswith("http"):
      gLogger.info("Using HTTPS for service %s" % serviceName)
      rpc = TornadoClient(*args, **kwargs)
    else:
      rpc = RPCClient(*args, **kwargs)
  except Exception as e:
    # If anything wen't wrong in the resolution, we return default RPCClient
    # So the comportement is exactly the same as before implementation of Tornado
    rpc = RPCClient(*args, **kwargs)
  return rpc
