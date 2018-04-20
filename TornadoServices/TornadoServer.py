"""
TORNADO SERVER
Receive RPC and return JSON to client
Also manage services start/stop 
"""

__RCSID__ = "$Id$"

from tornado.httpserver import HTTPServer
from tornado.web import RequestHandler, Application, url
from tornado.ioloop import IOLoop
from tornado.escape import json_encode
from DIRAC import S_OK, gLogger
from fakeDiracServices import DiracServices
from RPCTornadoHandler import RPCTornadoHandler
import ssl, os

''' It work, but it's also useless...
class StartServiceHandler(RequestHandler):
  """
  This class start a service throught DiracServices
  """
  def initialize(self, DiracServices):
    self.diracServices = DiracServices

  def get(self, service):
    self.diracServices.startService(service)
    self.write(json_encode(S_OK("Service started at /Service/"+service)))

class StopServiceHandler(RequestHandler):
  """
  This class stop a service
  """
  def initialize(self, DiracServices):
    self.diracServices = DiracServices

  def get(self, service):
    self.diracServices.stopService(service)
    self.write(json_encode(S_OK("Service "+service+" stopped")))
'''



def startTornado():
  gLogger.notice("TORNADO RESTART")
  diracServices = DiracServices()
  router = Application([
      url(r"/Service/([A-Za-z0-9/]+)/([A-Za-z0-9]+)", RPCTornadoHandler, dict(DiracServices=diracServices)),
      #url(r"/Start/([A-Za-z0-9/]+)", StartServiceHandler, dict(DiracServices=diracServices)),
      #url(r"/Stop/([A-Za-z0-9/]+)", StopServiceHandler, dict(DiracServices=diracServices))
  ], debug=True)


  diracServices.startService('Framework/User')

  cert_dir = '/root/dev/etc/grid-security/'


  #Define SSLContext
  ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

  # Load host certificates
  # TODO: Dynamic path
  ssl_ctx.load_cert_chain(os.path.join(cert_dir, "hostcert.pem"),
                          os.path.join(cert_dir, "hostkey.pem"))
  ssl_ctx.load_verify_locations(os.path.join('/root/dev/etc/grid-security/','hostcert.pem'))


  # Force client to use certificate
  ssl_ctx.verify_mode = ssl.CERT_REQUIRED




  server = HTTPServer(router, ssl_options=ssl_ctx)
  server.listen(8888)
  IOLoop.current().start()

startTornado()