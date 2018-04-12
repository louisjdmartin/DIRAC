from DIRAC import gLogger
from UserHandler import UserHandler
"""
  This class manage services 
"""
class DiracServices():
  def __init__(self):
    self.services = {}


  """
    Here we load a service 
  """
  def startService(self,service):
    gLogger.notice('Starting '+ service)
    self.services[str(service)] = UserHandler()

  """
    Here we stop a service 
  """
  def stopService(self,service):
    gLogger.notice('Stopping '+ service)
    self.services[str(service)] = None

  """
    Here we give the handler from a started service
  """
  def getServiceHandler(self, serviceName):
    if(serviceName in self.services):
      return self.services[str(serviceName)]
    return None