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

debug = '--debug' in sys.argv
multiprocess = '--multiprocess' in sys.argv
port = 443
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

includeExtensionErrors()


serverToLaunch = TornadoServer(debug=debug, port=port)
serverToLaunch.startTornado(multiprocess=multiprocess)
