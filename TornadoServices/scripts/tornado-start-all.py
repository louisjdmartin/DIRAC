#!/usr/bin/env python
########################################################################
# File :   tornado-start-all
# Author : Louis MARTIN
########################################################################
# Just run this script to start Tornado and all services
# You can add the port if needed, if not define get it from dirac.cfg or use default value (443)



__RCSID__ = "$Id$"
import sys
from DIRAC.ConfigurationSystem.Client.LocalConfiguration import LocalConfiguration
from DIRAC.FrameworkSystem.Client.Logger import gLogger
from DIRAC.TornadoServices.Server.TornadoServer import TornadoServer

localCfg = LocalConfiguration()

port = None
if len(sys.argv)>1:
  try:
    port = int(sys.argv[1])
  except ValueError:
    pass


localCfg.addMandatoryEntry("/DIRAC/Setup")

localCfg.addDefaultEntry("LogLevel", "INFO")
localCfg.addDefaultEntry("LogColor", True)
resultDict = localCfg.loadUserData()
gLogger.initialize('Tornado', "/")
if not resultDict['OK']:
  gLogger.error("There were errors when loading configuration", resultDict['Message'])
  sys.exit(1)



serverToLaunch = TornadoServer(port=port)
serverToLaunch.startTornado()
