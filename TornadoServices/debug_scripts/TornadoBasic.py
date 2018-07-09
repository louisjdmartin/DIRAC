"""
TORNADO SERVER
Receive RPC and return JSON to client
"""

__RCSID__ = "$Id$"
import ssl
import os
import DIRAC
from DIRAC import gLogger, S_ERROR

from tornado.httpserver import HTTPServer
from tornado.web import Application, url
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler




def startTornado():
 
  router = Application([url("/", displayHandler)])

  cert_dir = "%s/etc/grid-security/" % DIRAC.rootPath

  # Define SSLContext
  ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH, cafile=os.path.join(cert_dir, "hostcert.pem"))

  # Force client to use certificate
  ssl_ctx.verify_mode = ssl.CERT_REQUIRED

  # Load host certificates
  ssl_ctx.load_cert_chain(os.path.join(cert_dir, "hostcert.pem"),
                          os.path.join(cert_dir, "hostkey.pem"))

  # Start server
  server = HTTPServer(router, ssl_options=ssl_ctx)
  try:
    server.listen(443)
  except Exception as e:
    gLogger.fatal(e)
    return S_ERROR()
  IOLoop.current().start()


class displayHandler(RequestHandler):
  def get(self):
    cert = self.request.get_ssl_certificate() #False =  dictionnaire, True=Binaire
    print cert

startTornado()