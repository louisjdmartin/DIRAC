from tornado.httputil import HTTPHeaders
from tornado.httpclient import HTTPRequest, HTTPResponse,HTTPClient
from tornado.escape import json_decode,url_escape

class RPCClient(object):
  def __init__(self, service):
    """ 
      Defining usefull variables
      ==> Should be generated with dirac.cfg
    """
    self.service  = service
    self.port     = 8888
    self.domain   = 'localhost'
    self.protocol = 'http'
    self.RPCroot  = '/'

    self.rootUrl = self.protocol+"://"+self.domain+":"+str(self.port)+self.RPCroot

  def __getattr__(self,attrname):
    """ 
      Return the RPC call procedure
    """
    def call(*args):
      return self.RPC(attrname, *args)
    return call

  def RPC(self, procedure, *args):
    """
      This function call a remote service
    """

    # Init the HTTP Client
    http_client = HTTPClient()

    # Write arguments in HTTP headers
    h=HTTPHeaders()
    if args:
      for i in args:
        h.add("args", url_escape(str(i)))

    # Send the request
    request = HTTPRequest(self.rootUrl+"Service/"+self.service+":"+procedure, headers=h)
    response = http_client.fetch(request)


    # Return decoded response
    return json_decode(response.body)
