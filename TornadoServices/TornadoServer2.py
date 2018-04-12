from tornado.httpserver import HTTPServer
from tornado.httpclient import HTTPError
from tornado.web import RequestHandler, Application
from tornado.routing import Router
from tornado.ioloop import IOLoop
from tornado.escape import json_encode, url_unescape
from DIRAC import S_OK, S_ERROR, gLogger
from tornado.web import url
from fakeDiracServices import DiracServices
from RPCTornadoHandler import RPCTornadoHandler

"""
  This class start a service throught DiracServices
"""
class StartServiceHandler(RequestHandler):
  def initialize(self, DiracServices):
    self.DiracServices = DiracServices

  def get(self, service):
    self.DiracServices.startService(service)
    self.write(json_encode(S_OK("Service started at /Service/"+service)))

"""
  This class stop a service
"""
class StopServiceHandler(RequestHandler):
  def initialize(self, DiracServices):
    self.DiracServices = DiracServices

  def get(self, service):
    self.DiracServices.stopService(service)
    self.write(json_encode(S_OK("Service "+service+" stopped")))



"""
  Initiate Tornado Server
"""
DiracServices = DiracServices()
router = Application([
    url(r"/Service/([A-Za-z0-9/]+):([A-Za-z0-9]+)", RPCTornadoHandler,    dict(DiracServices=DiracServices)),
    url(r"/Start/([A-Za-z0-9/]+)",                  StartServiceHandler,  dict(DiracServices=DiracServices)),
    url(r"/Stop/([A-Za-z0-9/]+)",                   StopServiceHandler,   dict(DiracServices=DiracServices))
  ])


DiracServices.startService('Framework/user')
server = HTTPServer(router)
server.listen(8888)
IOLoop.current().start()