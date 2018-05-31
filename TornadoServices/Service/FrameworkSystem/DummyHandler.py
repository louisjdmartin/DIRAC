from TornadoService import TornadoService
from DIRAC import S_OK, S_ERROR

class DummyHandler(TornadoService):
  
  #LOCATION = "Framework/Dummy"

  auth_true = ['all']
  def export_true(self):
    return S_OK()

  auth_false = ['all']
  def export_false(self):
    return S_ERROR()

