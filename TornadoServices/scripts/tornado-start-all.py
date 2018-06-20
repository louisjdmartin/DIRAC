#!/usr/bin/env python
########################################################################
# File :   tornado-start-all
# Author : Louis MARTIN
########################################################################
__RCSID__ = "$Id$"

import sys
from DIRAC.ConfigurationSystem.Client.LocalConfiguration import LocalConfiguration
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC.FrameworkSystem.Client.Logger import gLogger
from DIRAC.Core.Utilities.DErrno import includeExtensionErrors
from DIRAC.TornadoServices.Server.TornadoServer import TornadoServer
from DIRAC.ConfigurationSystem.Client.PathFinder import getSystemInstance

localCfg = LocalConfiguration()
#if value and value.lower() in ( "yes", "true", "y" ):


## TODO a reecrire !

localCfg.addMandatoryEntry("/DIRAC/Setup")
localCfg.addDefaultEntry("LogLevel", "INFO")
localCfg.addDefaultEntry("LogColor", True)
resultDict = localCfg.loadUserData()
if not resultDict['OK']:
  gLogger.initialize(serverName, "/")
  gLogger.error("There were errors when loading configuration", resultDict['Message'])
  sys.exit(1)

includeExtensionErrors()


serverToLaunch = TornadoServer()
serverToLaunch.startTornado()
