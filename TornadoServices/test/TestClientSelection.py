
import os
import re


from pytest import mark, fixture

from DIRAC.TornadoServices.Client.RPCClientSelector import RPCClientSelector
from DIRAC.TornadoServices.Client.ClientSelector import ClientSelector
from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient
from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC.ConfigurationSystem.private.ConfigurationClient import ConfigurationClient
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC.Core.Utilities.CFG import CFG
from DIRAC.Core.Base.Client import Client
from DIRAC.Core.DISET.private.InnerRPCClient import InnerRPCClient

parametrize = mark.parametrize

"""
    Unit test on client selection:
        - By default: RPCClient should be used
        - If we use Tornado service TornadoClient is used

    Should work with
        - 'Component/Service'
        - URL
        - List of URL

    Mock Config:
        - Service using HTTPS with Tornado
        - Service using Diset
"""

testCfgFileName = 'test.cfg'


@fixture()
def config(request):
  """
    fixture is the pytest way to declare initalization function.
    Scope = module significate that this function will be called only time for this file.
    If no scope precised it call config for each test.

    This function can have a return value, it will be the value of 'config' argument for the tests
  """

  cfgContent = '''
  DIRAC
  {
    Setup=TestSetup
    Setups
    {
      TestSetup
      {
        WorkloadManagement=MyWM
      }
    }
  }
  Systems
  {
    WorkloadManagement
    {
      MyWM
      {
        URLs
        {
          ServiceDips = dips://server1:1234/WorkloadManagement/ServiceDips,dips://server2:1234/WorkloadManagement/ServiceDips
          ServiceHttps = https://server1:1234/WorkloadManagement/ServiceHttps,https://server2:1234/WorkloadManagement/ServiceHttps
        }
      }
    }
  }
  Operations{
    Defaults
    {
      MainServers = gw1, gw2
    }
  }
  '''
  with open(testCfgFileName, 'w') as f:
    f.write(cfgContent)
  gConfig = ConfigurationClient(fileToLoadList=[testCfgFileName])  # we replace the configuration by our own one.
  setup = gConfig.getValue('/DIRAC/Setup', '')
  wm = gConfig.getValue('DIRAC/Setups/' + setup + '/WorkloadManagement', '')

  def tearDown():
    """
      This function is called at the end of the test.
    """
    try:
      os.remove(testCfgFileName)
    except OSError:
      pass
    # SUPER UGLY: one must recreate the CFG objects of gConfigurationData
    # not to conflict with other tests that might be using a local dirac.cfg
    gConfigurationData.localCFG = CFG()
    gConfigurationData.remoteCFG = CFG()
    gConfigurationData.mergedCFG = CFG()
    gConfigurationData.generateNewVersion()

  # request is given by @fixture decorator, addfinalizer set the function who need to be called after the tests
  request.addfinalizer(tearDown)


client_imp = (
    (TornadoClient, 'WorkloadManagement/ServiceHttps'),
    (TornadoClient, 'https://server1:1234/WorkloadManagement/ServiceHttps'),
    (TornadoClient, 'https://server1:1234/WorkloadManagement/ServiceHttps,https://server2:1234/WorkloadManagement/ServiceHttps'),
    (RPCClient, 'WorkloadManagement/ServiceDips'),
    (RPCClient, 'dips://server1:1234/WorkloadManagement/ServiceDips'),
    (RPCClient, 'dips://server1:1234/WorkloadManagement/ServiceDips,dips://server2:1234/WorkloadManagement/ServiceDips'),
)


@parametrize('client', client_imp)
def test_selection_when_using_RPCClientSelector(client, config):
  """
    One way to call service is to use RPCClient or TornadoClient
    If service is HTTPS, it must return client who work with tornado (TornadoClient)
    else it must return the RPCClient
  """
  clientWanted = client[0]
  component_service = client[1]
  clientSelected = RPCClientSelector(component_service)
  assert isinstance(clientSelected, clientWanted)


@parametrize('client', client_imp)
def test_selection_when_inherit_from_Client(client, config):
  """
    Another way to call a service is to create a class who inherit from DIRAC.Core.Base.Client
    The class have a method who instanciate the RPCClient (or TornadoClient)
    If service is HTTPS, it must return client who work with tornado (TornadoClient)
    else it must return the RPCClient
  """
  clientWanted = client[0]
  component_service = client[1]

  clientInstance = ClientClass(component_service)
  clientSelected = clientInstance._getRPC()
  assert isinstance(clientSelected, clientWanted)


class ClientClass(ClientSelector):
  """
    This class is just for the test of inherit
  """

  def __init__(self, component_service, **kwargs):
    ClientSelector.__init__(self, **kwargs)
    self.setServer(component_service)


error_component = (
    'Too/Many/Sections',
    'JustAName',
    "InexistantComponent/InexistantService",
    "dummyProtocol://dummy/url")


@parametrize('component_service', error_component)
def test_error(component_service, config):
  """
    In any other cases (including error cases) it must return RPCClient by default
    This test is NOT testing if RPCClient handle the errors
    It just test that we get RPCClient and not Tornadoclient
  """
  clientSelected = RPCClientSelector(component_service)
  assert isinstance(clientSelected, RPCClient)


def test_interface():
  """
    Interface of TornadoClient MUST contain at least interface of RPCClient.
    BUT a __getattr__ method extends this interface with interface of InnerRPCClient.
  """
  interfaceTornadoClient = dir(TornadoClient)
  interfaceRPCClient = dir(RPCClient) + dir(InnerRPCClient)
  for element in interfaceRPCClient:
    # We don't need to test private methods / attribute
    # Private methods/attribute starts with __
    # dir also return private methods named with something like  _ClassName__PrivateMethodName
    if not element.startswith('__') and re.match(r'_[A-Za-z]+__[A-Za-z0-9_]+', element) is None:
      assert element in interfaceTornadoClient
