from DIRAC.Core.Base.Script import parseCommandLine
parseCommandLine()
from DIRAC import gConfig
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData


# print "user server certficate", gConfig.useServerCertificate()
# gConfigurationData.setOptionInCFG( '/DIRAC/Security/UseServerCertificate', 'true') 
# # print "user server certficate now", gConfig.useServerCertificate()

# delegatedDN = "/O=Volunteer Computing/O=CERN/CN=MrBoinc/emailAddress=something@somewhere.cern.ch"

from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient
from DIRAC.Core.DISET.RPCClient import RPCClient
#service = TornadoClient('Framework/User', useCertificates=True, delegatedDN=delegatedDN)
#service = RPCClient('Framework/UserDirac', useCertificates=True, delegatedDN=delegatedDN)
#service = RPCClient('Framework/UserDirac')
service = TornadoClient('https://MrBoincHost:443/Framework/User')
rep = service.listUsers()
print rep['OK']
if not rep['OK']:
    print rep['Message']
    for e in rep['CallStack']:
        print e
