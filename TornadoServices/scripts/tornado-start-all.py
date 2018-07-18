#!/usr/bin/env python
########################################################################
# File :   tornado-start-all
# Author : Louis MARTIN
########################################################################
# Just run this script to start Tornado and all services
# You can add the port if needed, if not define get it from dirac.cfg or use default value (443)

__RCSID__ = "$Id$"


# Must be define BEFORE any dirac import
import os
import sys
os.environ['USE_TORNADO_IOLOOP'] = "True"


from DIRAC.FrameworkSystem.Client.Logger import gLogger
from DIRAC.TornadoServices.Server.TornadoServer import TornadoServer
from DIRAC.Core.Base import Script

from DIRAC.ConfigurationSystem.Client.LocalConfiguration import LocalConfiguration

from DIRAC.Core.Utilities.DErrno import includeExtensionErrors

#Script.parseCommandLine(ignoreErrors = True)
localCfg=LocalConfiguration()
localCfg.addMandatoryEntry( "/DIRAC/Setup" )
localCfg.addDefaultEntry( "/DIRAC/Security/UseServerCertificate", "yes" )
localCfg.addDefaultEntry( "LogLevel", "INFO" )
localCfg.addDefaultEntry( "LogColor", True )
resultDict = localCfg.loadUserData()
if not resultDict[ 'OK' ]:
  gLogger.initialize( serverName, "/" )
  gLogger.error( "There were errors when loading configuration", resultDict[ 'Message' ] )
  sys.exit( 1 )

includeExtensionErrors()


gLogger.initialize('Tornado', "/")

port = None
if len(sys.argv)>1:
  try:
    port = int(sys.argv[1])
  except ValueError:
    pass




serverToLaunch = TornadoServer(port=port)
serverToLaunch.startTornado()
