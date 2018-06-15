"""
    In this test we want to check if Tornado generate the same credentials dictionnary as DIRAC.
    It also test if the correct certificates are sended by client. 

    To run this test you must have the handlers who returns credentials dictionnary.
    Handlers are diracCredDictHandler and tornadoCredDictHandler just returns these dictionnary 
    and are stored in DIRAC/FrameworkSystem/Service
  
    Then you have to start tornado using script tornado-start-all.py in DIRAC/TornadoServices/scripts 
    before running test

    In configuration it have to be set as normal services, it will look like:

    ```
    # In Systems/Service/<instance>/Framework
     Services
      {
        tornadoCredDict
        {
          # it can be empty, port is 443 (https) and no settings are required, but must be present
        }
        diracCredDict
        {
          Port = 3444
          DisableMonitoring = yes
        }
      }
    ```

    ```
    URLs
      {
        tornadoCredDict = https://localhost:443/Framework/tornadoCredDict
        diracCredDict = dips://MrBoincHost:3444/Framework/diracCredDict
      }
    ```
  
"""

import pytest
from DIRAC import gConfig
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData

from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient
from DIRAC.Core.DISET.RPCClient import RPCClient
from pytest import mark, fixture
parametrize = mark.parametrize


def get_RPC_returnedValue(serviceName, RPCClient):
  """
    Get credentials extracted tornado server or Dirac server
  """
  service = RPCClient(serviceName) 
  return service.credDict()

def get_all_returnedValues():
  serviceNameTornado = 'Framework/tornadoCredDict'
  serviceNameDirac = 'Framework/diracCredDict'
  repTornado = get_RPC_returnedValue(serviceNameTornado,TornadoClient)
  repDirac = get_RPC_returnedValue(serviceNameDirac, RPCClient)
  return (repTornado, repDirac)

@parametrize('UseServerCertificate', ('True', 'False'))
def test_return_credential_are_equals(UseServerCertificate):
  gConfigurationData.setOptionInCFG('/DIRAC/Security/UseServerCertificate', UseServerCertificate) 

  (repTornado, repDirac) = get_all_returnedValues()

  #Service returns credentials
  assert repDirac['Value'] == repTornado['Value'] 


@parametrize('UseServerCertificate', ('True', 'False'))
def test_rpcStubs_are_equals(UseServerCertificate):
  (repTornado, repDirac) = get_all_returnedValues()

  # rep['rpcStub'] is at form (rpcStub, method, args) where rpcStub is tuple with (serviceName, kwargs)
  assert repTornado['rpcStub'][0][0] != repDirac['rpcStub'][0][0] #Services name are different
  assert repTornado['rpcStub'][0][1] == repDirac['rpcStub'][0][1] #Check kwargs returned by rpcStub
  assert repTornado['rpcStub'][1:] == repDirac['rpcStub'][1:] #Check method/args



