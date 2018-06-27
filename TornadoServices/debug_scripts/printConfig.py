import DIRAC

from DIRAC.Core.Base.Script import parseCommandLine
parseCommandLine()

from DIRAC import gConfig

tree = gConfig.getConfigurationTree()


print 42*"="
if not tree['OK']:
  print tree['Message']
else:
  for key in tree['Value']:
    print key, tree['Value'][key]