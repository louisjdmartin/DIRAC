from DIRAC import S_OK, S_ERROR, gLogger
from fakeDiracServices import DiracServices
from tornado.web import RequestHandler
from tornado.escape import json_encode, url_unescape


""" 
  This handler get Remote Request and execute them
"""
class RPCTornadoHandler(RequestHandler):

  """ 
    initialize
    Get the services opened
    Get arguments from headers (if exists)
  """
  def initialize(self, DiracServices):
    self.DiracServices = DiracServices
    self.args = self.request.headers.get_list('args')
    for i in range(len(self.args)):
      self.args[i]=url_unescape(self.args[i])

  """ 
    HTTP GET
    Get the correct handler from a service already loaded and execute RPC Call
  """
  def get(self, service, RPC):
    gLogger.notice('======== HTTP GET Request ========')
    gLogger.notice('Service:   ' + service             )
    gLogger.notice('Procedure: ' + RPC                 )
    gLogger.notice('Arguments: ' + str(self.args)      )
    gLogger.notice('==================================')

    handler = self.DiracServices.getServiceHandler(service)

    if(handler == None):
      self.write(json_encode(S_ERROR('Service not started')))
      return

    """ Here the call can fail (Rong  number of arguments for example) """
    try:
      method = getattr(handler, RPC)
      self.write(json_encode(method(*self.args)))
    except Exception, e:
      self.write(json_encode(S_ERROR(str(e))))
    