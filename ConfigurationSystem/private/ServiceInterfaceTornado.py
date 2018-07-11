
from tornado import gen
from tornado.ioloop import IOLoop
from DIRAC.ConfigurationSystem.private.ServiceInterfaceBase import ServiceInterfaceBase
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC import gLogger

class ServiceInterfaceTornado(ServiceInterfaceBase):

  def __init__(self, sURL):
    ServiceInterfaceBase.__init__(self, sURL)
    self.__launchCheckSlaves()

  def __launchCheckSlaves( self ): 
    IOLoop.current().spawn_callback(self.run)
    gLogger.info( "Starting purge slaves thread" )


  def run( self ):
    while True:
      yield gen.sleep(gConfigurationData.getSlavesGraceTime())
      self._checkSlavesStatus()