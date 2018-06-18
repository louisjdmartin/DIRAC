"""
  TornadoClient is equivalent of RPCClient in HTTPS.
  Usage of TornadoClient is the same as RPCClient, you can instanciate TornadoClient with
  complete url (https://domain/component/service) or just "component/service".

  Main changes:
    - KeepAliveLapse is removed, requests library manage it himself.
    - nbOfRetry (defined as private attribute) is remove, requests library manage it himself.
    - Underneath it use HTTP POST protocol and JSON

  Changes to discuss:
    - Remove the CallStack returned by server when server send S_ERROR after failed authentication
       (or at least make it configurable, so it can be accessible in dev/debug but not in production for example)
"""

from DIRAC.Core.Utilities.JEncode import encode
from DIRAC.TornadoServices.Client.private.TornadoBaseClient import TornadoBaseClient


class TornadoClient(TornadoBaseClient):
  """
    Client for calling tornado services
    Interface is based on RPCClient interface
  """

  def __getattr__(self, attrname):
    """
      Return the RPC call procedure
      :param str attrname: Name of the procedure we are trying to call
      :return: RPC procedure
    """
    def call(*args):
      """
        Just returns the right function for RPC Call
      """
      return self.executeRPC(attrname, *args)
    return call

  def executeRPC(self, method, *args):
    """
      This function call a remote service
      :param str procedure: remote procedure name
      :param args: list of arguments
      :return: decoded response from server, server may return S_OK or S_ERROR
    """
    rpcCall = {'method': method, 'args': encode(args)}
    # Start request
    retVal = self._request(rpcCall)
    retVal['rpcStub'] = (self._getBaseStub(), method, args)
    return retVal


def executeRPCStub( rpcStub ):
  """
  Playback a stub
  # Copy-paste from DIRAC.Core.DISET.RPCClient with RPCClient changed into TornadoClient
  """
  #Generate a RPCClient with the same parameters
  rpcClient = TornadoClient( rpcStub[0][0], **rpcStub[0][1] )
  #Get a functor to execute the RPC call
  rpcFunc = getattr( rpcClient, rpcStub[1] )
  #Reproduce the call
  return rpcFunc( *rpcStub[2] )


# NOTE pour utilisation requests
# https://lukasa.co.uk/2017/02/Configuring_TLS_With_Requests/
# Depuis requests 2.12 certains chiffrements ne sont plus acceptees
# Passer Tornado en AES ?
