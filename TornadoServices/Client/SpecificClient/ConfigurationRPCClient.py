"""
  Custom TornadoClient for Configuration System
  Used like a normal client, should be instanciated if and only if we use the configuration service

  Because of limitation with JSON some datas are encoded in base64

"""

from base64 import b64encode, b64decode

from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient

class ConfigurationRPCClient(TornadoClient):
  """
    The specific client for configuration system.
    To avoid JSON limitation it adds base 64 encoding
  """


  def getCompressedData(self):
    """
      Transmit request to service and get data in base64,
      it decode base64 before returning

      :returns str:Configuration data, compressed
    """
    retVal = self.executeRPC('getCompressedData')
    if retVal['OK']:
      retVal['Value'] = b64decode(retVal['Value'])
    return retVal

  def getCompressedDataIfNewer(self, sClientVersion):
    """
      Transmit request to service and get data in base64,
      it decode base64 before returning.

      :returns str:Configuration data, if changed, compressed
    """
    retVal = self.executeRPC('getCompressedDataIfNewer', sClientVersion)
    if retVal['OK'] and 'data' in retVal['Value']:
      retVal['Value']['data'] = b64decode(retVal['Value']['data'])
    return retVal

  def commitNewData(self, sData):
    """
      Transmit request to service by encoding data in base64.
    """
    return self.executeRPC('commitNewData', b64encode(sData))