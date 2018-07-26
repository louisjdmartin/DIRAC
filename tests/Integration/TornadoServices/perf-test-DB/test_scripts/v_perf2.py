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
    # If we want we can force to use dirac
    #if len(sys.argv) > 2 and sys.argv[2].lower() == 'dirac':
    #  self.client = RPCClient('Framework/User')
    #else:
    #  self.client = TornadoClient('Framework/User')
    self.client = RPCClientSelector('Framework/User2', timeout=30)
    #print os.environ['PYTHONOPTIMIZE']
    return

  def run(self):
    #Generate random name
    s = str(int(random.random()*100))
    s2= str(int(random.random()*100))
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
