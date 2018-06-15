import os
import ssl
import httplib
import urllib
import requests
import urlparse
import time

import DIRAC
from DIRAC import S_OK, gLogger
from DIRAC.Core.Utilities.JEncode import encode, decode
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

  


# NOTE pour utilisation requests
# https://lukasa.co.uk/2017/02/Configuring_TLS_With_Requests/
# Depuis requests 2.12 certains chiffrements ne sont plus acceptees
# Passer Tornado en AES ?
