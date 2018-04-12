""" Test for UserDB
    Testing if basic operation works
"""


from string import printable
import datetime
import sys

from hypothesis import given, settings
from hypothesis.strategies import text

from TornadoClient import RPCClient

@given(text(printable),text(printable))
def test_insert_get_update_db(s,s2):
    #s=str(s)
    
    # Create a user
    service=RPCClient('Framework/User')
    
    # Create a user
    newUser = service.addUser(s)
    userID = newUser['Value']

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



