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

Script.parseCommandLine(ignoreErrors = True)

gLogger.initialize('Tornado', "/")

port = None
if len(sys.argv)>1:
  try:
    port = int(sys.argv[1])
  except ValueError:
    pass




serverToLaunch = TornadoServer(port=port)
serverToLaunch.startTornado()
