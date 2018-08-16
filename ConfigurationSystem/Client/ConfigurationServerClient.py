"""
  Used like a normal client, should be instanciated if and only if we use the configuration service

  Because of limitation with JSON some datas are encoded in base64

  IMPORTANT NOTE: for now this is only a preparation for HTTPS,
  ConfigurationServerClient is used but httpsClient is not used for now

"""

from DIRAC.Core.Base.Client import Client


class ConfigurationServerClient(Client):
  """
    Specific client to speak with ConfigurationServer.

    This class must contain at least the JSON decoder dedicated to
    the Configuration Server.

    You can implement more logic or function to the client here if needed,
    RPCCall can be made inside this class with executeRPC method.
  """

  # The JSON decoder for Configuration Server
  pass
