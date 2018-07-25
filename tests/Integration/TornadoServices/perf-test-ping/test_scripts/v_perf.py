#from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient
#from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC.TornadoServices.Client.RPCClientSelector import RPCClientSelector
from time import time
from random import randint
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
    self.client = RPCClientSelector('Framework/User', timeout=30)
    #print os.environ['PYTHONOPTIMIZE']
    return

  def run(self):
    assert (self.client.ping()['OK'] == True), 'error'
