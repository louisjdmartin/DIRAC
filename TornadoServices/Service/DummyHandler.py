from RPCTornadoHandler import RPCTornadoHandler
from DIRAC import S_OK, S_ERROR

class DummyHandler(RPCTornadoHandler):
  
  auth_true = ['all']
  def export_true(self):
    return S_OK()

  auth_false = ['all']
  def export_false(self):
    return S_ERROR()

