import tornado.ioloop
import tornado.web
import tornado.gen as gen

from UserHandler import UserHandler
from tornado.web import url
from tornado import httpserver
from tornado.escape import json_encode, url_unescape
from DIRAC import S_OK

class StartServiceHandler(tornado.web.RequestHandler):
  """ TODO: Check if service not already launched """
  def get(self, service):
    print ('STARTING ' + service + ' at URL /Service/'+service)
    #Here we should start the RIGHT service
    userhandler = UserHandler()

    tornado.ioloop.IOLoop.current().spawn_callback(fake_background_loop, service)

    app.add_handlers(r".*",[
      url(r"/Service/"+service+":([A-Za-z0-9]+)", ServiceHandler, dict(handler=userhandler))
    ])

    self.write(json_encode(S_OK('Service started at /Service/'+service)))

class ServiceHandler(tornado.web.RequestHandler):


  """ Initialize, call at every request """
  def initialize(self, handler):
    #This function get the arguments
    #If user send arguments we suppose that they are send in the headers
    self.args = self.request.headers.get_list('args')
    for i in range(len(self.args)):
      self.args[i]=url_unescape(self.args[i])

    # Here we get the Handler from the service we want to call (already initialised)
    self.handler = handler
    
    print ('INIT ServiceHandler')


  """ When we use HTTP GET it call this method, we can also define 'post'
      Arguments are from the URL
      Here we get the service name but it's useless, it's just to proove that we can get service name
      in final version we may load the good services class and methods
  """
  def get(self, RPC):
    #This code should be rewrited, but we can return with 
    #self.write(json_encode(S_OK(ReturnedValue)))
    #self.write() simply write in HTTP Response

    method = getattr(self.handler, RPC)
    self.write(json_encode(method(*self.args)))



def make_app():
  """
  Init Tornado Webservice
  Syntax: url(r'UrlWithRegex', HandlerCalledWhenUrlMatch)
  ==> You can add arguments from URL by using ()
  Generate from dirac.cfg?
  """
  return tornado.web.Application([
    #url(r"/Service/Framework/User:([A-Za-z0-9]+)", ServiceHandler, dict(handler=userhandler)),
    url(r"/Start/([A-Za-z0-9/]+)", StartServiceHandler)
  ])

"""
  Just some test
"""
@gen.coroutine
def fake_background_loop(s):
  while True:
    wait = gen.sleep(10)              #Start sleep(10)
    yield background_task(s) #Execute task 
    yield wait                        #Wait the end of sleep(10)

def background_task(s):
  print('background_task:' + s)





if __name__ == "__main__":
  """ Start Tornado Webservice"""

  app = make_app()
  server = httpserver.HTTPServer(app)
  server.listen(8888)
  tornado.ioloop.IOLoop.current().start()

