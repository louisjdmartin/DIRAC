from TornadoClient import TornadoClient
from time import time

class Transaction(object):
  def __init__(self):
    self.serviceTornado = TornadoClient('Framework/User')
    return

  def run(self):
    reponse = self.serviceTornado.listUsers()
    assert (reponse['OK'] == True)