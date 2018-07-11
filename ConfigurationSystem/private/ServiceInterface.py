""" Threaded implementation of services
"""

import time
import threading
from DIRAC import gLogger

from DIRAC.ConfigurationSystem.private.ServiceInterfaceBase import ServiceInterfaceBase
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData

__RCSID__ = "$Id$"


class ServiceInterface(ServiceInterfaceBase, threading.Thread):

  def __init__( self, sURL ):
    threading.Thread.__init__(self)
    ServiceInterfaceBase.__init__(self, sURL)
    self.__launchCheckSlaves()


  def __launchCheckSlaves( self ): ## TO REDEFINE !
    gLogger.info( "Starting purge slaves thread" )
    self.setDaemon( 1 )
    self.start()


  def run( self ):
    while True:
      iWaitTime = gConfigurationData.getSlavesGraceTime()
      time.sleep( iWaitTime )
      self._checkSlavesStatus()