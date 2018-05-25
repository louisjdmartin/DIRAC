#!/usr/bin/env python
########################################################################
# File :   dirac-tornado-service
# Author : Louis MARTIN
########################################################################
__RCSID__ = "$Id$"

import sys
from DIRAC.ConfigurationSystem.Client.LocalConfiguration import LocalConfiguration
from DIRAC.FrameworkSystem.Client.Logger import gLogger
from DIRAC.Core.Utilities.DErrno import includeExtensionErrors
from DIRAC.TornadoServices.TornadoServer import TornadoServer

localCfg = LocalConfiguration()

positionalArgs = localCfg.getPositionalArguments()
if len( positionalArgs ) == 0:
  gLogger.fatal( "You must specify which server to run!" )
  sys.exit( 1 )

serverName = positionalArgs[0]
localCfg.setConfigurationForServer(serverName)
localCfg.addMandatoryEntry("/DIRAC/Setup")
localCfg.addDefaultEntry( "LogLevel", "INFO" )
localCfg.addDefaultEntry( "LogColor", True )
resultDict = localCfg.loadUserData()
if not resultDict[ 'OK' ]:
  gLogger.initialize( serverName, "/" )
  gLogger.error( "There were errors when loading configuration", resultDict[ 'Message' ] )
  sys.exit( 1 )

includeExtensionErrors()


serverToLaunch = TornadoServer(serverName)
serverToLaunch.startTornado()

