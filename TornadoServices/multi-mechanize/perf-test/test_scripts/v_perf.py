from TornadoClient import TornadoClient
from DIRAC.Core.DISET.RPCClient import RPCClient
from time import time
import sys

class Transaction(object):
  def __init__(self):
    #If we want we can force to use dirac
    if len(sys.argv)>2 and sys.argv[2].lower() == 'dirac':
        self.service = RPCClient('Framework/User')
    else:
        self.service = TornadoClient('Framework/User')
    return

  def run(self):
    reponse = self.service.listUsers()
    assert (reponse['OK'] == True)

