""" Test for UserDB
    Testing if basic operation works
"""


from string import printable
import datetime
import sys

from hypothesis import given, settings
from hypothesis.strategies import text

from DIRAC.Core.DISET.RPCClient import RPCClient as RPCClientDIRAC
from DIRAC.Core.Base.UserDB import UserDB
from TornadoClient import TornadoClient as RPCClientTornado

from pytest import mark
parametrize = mark.parametrize
"""
    cf DIRAC/Core/Utilities/test/Test_Encode.py 
    from pytest import mark, approx, raises
    parametrize = mark.parametrize
"""
rpc_imp = (RPCClientTornado, RPCClientDIRAC)
@parametrize('rpc', rpc_imp)
@given(s=text(printable, max_size=64),s2=text(printable, max_size=64))
@settings(deadline=None,max_examples=10)
def test_insert_get_update_service(rpc,s,s2):
    RPCClient = rpc
    service=RPCClient('Framework/User')   
    # Create a user
    newUser = service.addUser(s)
    userID = int(newUser['Value'])
    # Check if user exist and name is correct
    User = service.getUserName(userID)
    assert User['OK'] == True
    assert User['Value'] == s
    # Check if update work
    service.editUser(userID, s2)
    User = service.getUserName(userID)
    assert User['Value'] == s2
    # Delete a user
    service.removeUser(userID)
    deletedUser = service.getUserName(userID)
    # Check if User is deleted
    assert deletedUser['OK'] == False



