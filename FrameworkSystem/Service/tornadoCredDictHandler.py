from DIRAC.TornadoServices.Server.TornadoService import TornadoService
from DIRAC import S_OK, S_ERROR

class tornadoCredDictHandler(TornadoService):
  

  auth_credDict = ['all']
  def export_credDict(self):
    c = self.credDict
    del c['x509Chain']
    return S_OK(c)

