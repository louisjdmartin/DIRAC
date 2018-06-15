""" 
    Same class as DIRAC.Core.Base.Client but with _getRPC redefined to use the RPCClientSelector
    Just test, maybe it's better to modify inport in DIRAC.TornadoServices.Client.RPCClientSelector
"""
from DIRAC.Core.Base.Client import Client
from DIRAC.TornadoServices.Client.RPCClientSelector import RPCClientSelector

class ClientSelector(Client):
  """
    Exactly the same class as DIRAC.Core.Base.Client but with _getRPC redefined to include the RPCClientSelector
  """

  def _getRPC(self, rpc=None, url='', timeout=600):
    """ Return an RPCClient object constructed following the attributes.

        :param rpc: if set, returns this object
        :param url: url of the service. If not set, use self.serverURL
        :param timeout: timeout of the call
    """
    if not rpc:
      if not url:
        url = self.serverURL
      # HACK to manipulate private attributes of Client
      self._Client__kwargs.setdefault('timeout', timeout)
      rpc = RPCClientSelector(url, **self._Client__kwargs)
    return rpc