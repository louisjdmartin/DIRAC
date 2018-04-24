from DIRAC.Core.DISET.RPCClient import RPCClient
from time import time

class Transaction(object):
  def __init__(self):
    self.serviceDirac = RPCClient('Framework/User')
    return

  def run(self):
    reponse = self.serviceDirac.listUsers()
    assert (reponse['OK'] == True)