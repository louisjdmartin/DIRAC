"""
  Custom TornadoClient for Configuration System
  Used like a normal client, should be instanciated if and only if we use the configuration service

  Because of limitation with JSON some datas are encoded in base64

"""

from base64 import b64encode, b64decode

from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient
from DIRAC.TornadoServices.Client.RPCClientSelector import RPCClientSelector

class ConfigurationClient(object):
  """
    The specific client for configuration system.
    To avoid JSON limitation it adds base 64 encoding
  """

  def __init__(self, *args, **kwargs):
    """
      Little trick for backward compatibility
      If we use Tornado it replace ConfigurationClient calls
      Else it just transmit them to RPCClient
    """
    self.__rpcClient = RPCClientSelector(*args, **kwargs)
    self.__isTornadoClient = isinstance(self.__rpcClient, TornadoClient)

  def __getattr__(self, attr):
    """
      For every attributes/methods not redefined, we transfer call to RPCClient
    """
    return getattr(self.__rpcClient, attr)

  def getCompressedData(self):
    """
      Transmit request to service and get data in base64,
      it decode base64 before returning

      :returns str:Configuration data, compressed
    """
    retVal = self.__rpcClient.getCompressedData()
    if self.__isTornadoClient and retVal['OK'] and 'data' in retVal['Value']:
      retVal['Value']['data'] = b64decode(retVal['Value']['data'])
    return retVal

  def getCompressedDataIfNewer(self, sClientVersion):
    """
      Transmit request to service and get data in base64,
      it decode base64 before returning.

      :returns str:Configuration data, if changed, compressed
    """
    retVal = self.__rpcClient.getCompressedDataIfNewer(sClientVersion)
    if self.__isTornadoClient and retVal['OK'] and 'data' in retVal['Value']:
      retVal['Value']['data'] = b64decode(retVal['Value']['data'])
    return retVal

  def commitNewData(self, sData):
    """
      Transmit request to service by encoding data in base64.
    """
    if self.__isTornadoClient:
      return self.executeRPC('commitNewData', b64encode(sData))
    return self.__rpcClient.commitNewData(sData)