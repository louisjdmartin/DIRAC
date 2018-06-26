"""
    Test if same service work on DIRAC and TORNADO
    Testing if basic operation works on a dummy example
    
    It's just normal services, entry in dirac.cfg are the same as usual.
    To start tornado use DIRAC/TornadoServices/scripts/tornado-start-all.py
    ```
    Services
      {
        User
        {
          # It can be empty, use port 443 (HTTPS)
        }
        UserDirac
        {
          Port = 3424
          DisableMonitoring = yes
          #HandlerPath = DIRAC/TornadoServices/Service/UserHandler.py
        }
      }
    ```

    ```
    URLs
      {
        User = https://MrBoincHost:443/Framework/User
        UserDirac = dips://localhost:3424/Framework/UserDirac
      }
    ```

"""

from DIRAC.Core.Base.Script import parseCommandLine
parseCommandLine()
from string import printable
import datetime
import sys

from hypothesis import given, settings
from hypothesis.strategies import text

from DIRAC.Core.DISET.RPCClient import RPCClient as RPCClientDIRAC
from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient as RPCClientTornado
from DIRAC.Core.Utilities.DErrno import ENOAUTH
from DIRAC import S_ERROR

from pytest import mark
parametrize = mark.parametrize

rpc_imp = ((RPCClientTornado, 'Framework/User'), (RPCClientDIRAC, 'Framework/UserDirac'))



# @parametrize('rpc', rpc_imp)
# @given(s=text(printable, max_size=64), s2=text(printable, max_size=64))
# @settings(deadline=None, max_examples=42)
# def test_basic_logic(rpc, s, s2):
#   service = rpc[0](rpc[1])

#   # Create a user
#   newUser = service.addUser(s)
#   userID = int(newUser['Value'])

#   # Check if user exist and name is correct
#   User = service.getUserName(userID)
#   assert User['OK']
#   assert User['Value'] == s

#   # Check if update work
#   service.editUser(userID, s2)
#   User = service.getUserName(userID)
#   assert User['Value'] == s2



@parametrize('rpc', rpc_imp)
def test_authorization(rpc):
  service = rpc[0](rpc[1])

  authorisation = service.unauthorized()
  assert authorisation['OK'] == False 
  assert authorisation['Message'] == S_ERROR(ENOAUTH, "Unauthorized query")['Message']



@parametrize('rpc', rpc_imp)
def test_unknown_method(rpc):
  service = rpc[0](rpc[1])

  unknownmethod = service.ThisMethodMayNotExist()
  assert unknownmethod['OK'] == False
  assert unknownmethod['Message'] == "Unknown method ThisMethodMayNotExist"



@parametrize('rpc', rpc_imp)
def test_ping(rpc):
  service = rpc[0](rpc[1])

  assert service.ping()['OK'] == True


@parametrize('rpc', rpc_imp)
@settings(deadline=None, max_examples=42)
@given(data=text(printable, max_size=64))
def test_echo(rpc, data):
  service = rpc[0](rpc[1])

  assert service.echo(data)['Value'] == data

#def test_whoami(): #Only in tornado
