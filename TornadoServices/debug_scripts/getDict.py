from DIRAC.Core.Base.Script import parseCommandLine
parseCommandLine()
from DIRAC import gConfig
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
print "user server certficate", gConfig.useServerCertificate()
gConfigurationData.setOptionInCFG( '/DIRAC/Security/UseServerCertificate', 'true') 
print "user server certficate now", gConfig.useServerCertificate()




from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient
serviceTornado = TornadoClient('Framework/tornadoCredDict')
#serviceTornado = TornadoClient('https://MrBoincHost:443/Framework/User')
repTornado = serviceTornado.credDict()


from DIRAC.Core.DISET.RPCClient import RPCClient
serviceTornado = RPCClient('Framework/diracCredDict')
repDirac = serviceTornado.credDict()




print "=================================== REPONSE ==================================="
for key in repDirac:
    if not key=='Value': #DisplayedAfter
        print '%s\n\tTornado\t%s\n\tDirac\t%s' % (key, repTornado[key], repDirac[key])

print "=================================== DICTIONNAIRE ==================================="
for key in repDirac['Value']:
    print '%s\n\tTornado\t%s\n\tDirac\t%s' % (key, repTornado['Value'][key], repDirac['Value'][key])