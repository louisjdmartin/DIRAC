#from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient
#from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC.TornadoServices.Client.RPCClientSelector import RPCClientSelector
from time import time
from random import random
import sys
import os
#from DIRAC import S_OK

class Transaction(object):
  def __init__(self):
    self.client = RPCClientSelector('Framework/User', timeout=30)
    return

  def run(self):
    #Generate random name
    s = str(int(random()*100))
    s2= str(int(random()*100))
    service = self.client
    #print service
    # Create a user
    newUser = service.addUser(s)
    userID = int(newUser['Value'])

    # Check if user exist and name is correct
    User = service.getUserName(userID)
    assert (User['OK'] == True), 'Error in getting user'
    assert (User['Value'] == s), 'Error on insertion'

    # Check if update work
    service.editUser(userID, s2)
    User = service.getUserName(userID)
    assert (User['Value'] == s2), 'Error on update'

    #assert (self.client.addUser()['OK'] == True), 'error'
