import pytest
from DIRAC import gConfig
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData

from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient
from DIRAC.Core.DISET.RPCClient import RPCClient
from pytest import mark
parametrize = mark.parametrize

@parametrize('UseServerCertificate', ('True', 'False'))
def test_coherence(UseServerCertificate):
  gConfigurationData.setOptionInCFG( '/DIRAC/Security/UseServerCertificate', UseServerCertificate) 

  serviceTornado = TornadoClient('Framework/tornadoCredDict')
  dictTornado = serviceTornado.credDict()['Value']

  serviceDirac = RPCClient('Framework/diracCredDict')
  dictDirac = serviceDirac.credDict()['Value']

  assert dictTornado==dictDirac