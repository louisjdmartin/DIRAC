"""
TORNADO SERVER
Receive RPC and return JSON to client
"""

__RCSID__ = "$Id$"
from DIRAC.FrameworkSystem.Service.UserDB import UserDB
from tornado.httpserver import HTTPServer
from tornado.web import RequestHandler, Application, url
from tornado.ioloop import IOLoop
from tornado.escape import json_encode
from tornado import gen
from DIRAC import S_OK, gLogger
from RPCTornadoHandler import TornadoUserHandler
import ssl, os



def startTornado():
  # Just for visual feedback when there is an autoreload
  # Must be deleted later
  gLogger.notice("TORNADO RESTART") 


  # TODO: Dynamic rooting (with dirac.cfg ?)
  userDB = UserDB()
  router = Application([
      url(r"/Service/Framework/User/([A-Za-z0-9]+)", TornadoUserHandler, dict(UserDB=userDB)),
  ], debug=True)


  # TODO: get path automatically
  cert_dir = '/root/dev/etc/grid-security/'


  #Define SSLContext
  ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
  #ssl_ctx = ssl.create_default_context()

  # Load host certificates
  ssl_ctx.load_cert_chain(os.path.join(cert_dir, "hostcert.pem"),
                          os.path.join(cert_dir, "hostkey.pem"))

  # TODO: get path automatically
  ssl_ctx.load_verify_locations(os.path.join('/root/dev/etc/grid-security/','hostcert.pem'))


  # Force client to use certificate
  ssl_ctx.verify_mode = ssl.CERT_REQUIRED





  # Start server
  server = HTTPServer(router, ssl_options=ssl_ctx)
  server.listen(8888)
  IOLoop.current().start()


startTornado()