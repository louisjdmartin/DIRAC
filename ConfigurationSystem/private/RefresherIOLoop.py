"""
  This class must be used ONLY by Refresher !

  It contains background activities for refresher, it works with IOLoop from Tornado.

  Each method have its docstring but you may refer to Tornado documentation about
  IOLoop who can be found here:

  - http://www.tornadoweb.org/en/stable/ioloop.html
  - http://www.tornadoweb.org/en/stable/guide/coroutines.html

  To run Refresher with this version you must define the USE_TORNADO_IOLOOP
  environement variable

 .. warning::

    You can't use this class without an IOLoop who is running.
    This class can be defined before starting IOLoop, background tasks
    will be delayed until the IOLoop start.
"""

import time

from tornado import gen
from tornado.ioloop import IOLoop

from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC import gLogger


class RefresherIOLoop(object):
  """
    Refresher adapted to work with Tornado an its IOLoop
  """



  def refreshConfigurationIfNeeded(self):
    """
      Trigger an automatic refresh, most of the time nothing happens because automaticUpdate is enabled.
      This function is called by gConfig.getValue most of the time.

      We disable pylint error because this class must be instanciated by a mixin to define the missing methods
    """
    if not self._refreshEnabled or self._automaticUpdate or not gConfigurationData.getServers(): #pylint: disable=no-member
      return
    if not self._lastRefreshExpired(): #pylint: disable=no-member
      return
    self._lastUpdateTime = time.time()
    IOLoop.current().run_in_executor(None, self._refresh) #pylint: disable=no-member
    return

  def autoRefreshAndPublish(self, sURL):
    """
      Start the autorefresh background task, called by ServiceInterface
      (the class behind the Configuration/Server handler)

      :param str sURL: URL of the configuration server
    """
    gLogger.debug("Setting configuration refresh as automatic")
    if not gConfigurationData.getAutoPublish():
      gLogger.debug("Slave server won't auto publish itself")
    if not gConfigurationData.getName():
      import DIRAC
      DIRAC.abort(10, "Missing configuration name!")
    self._url = sURL
    self._automaticUpdate = True

    # Tornado replacement solution to the classic thread
    # It start the method self.__refreshLoop on the next IOLoop iteration
    IOLoop.current().spawn_callback(self.__refreshLoop)

  @gen.coroutine
  def __refreshLoop(self):
    """
      Trigger the autorefresh when configuration is expired

      This task must use Tornado utilities to avoid blocking the ioloop and
      pottentialy deadlock the server.

      See http://www.tornadoweb.org/en/stable/guide/coroutines.html#looping
      for official documentation about this type of method.
    """
    while self._automaticUpdate:

      # This is the sleep from Tornado, like a sleep it wait some time
      # But this version is non-blocking, so IOLoop can continue execution
      yield gen.sleep(gConfigurationData.getPropagationTime())
      # Publish step is blocking so we have to run it in executor
      # If we are not doing it, when master try to ping we block the IOLoop
      yield IOLoop.current().run_in_executor(None, self.__AutoRefresh)

    @gen.coroutine
    def __AutoRefresh(self):
      """
        Auto refresh the configuration
        We disable pylint error because this class must be instanciated
        by a mixin to define the methods.
      """
      if self._refreshEnabled: #pylint: disable=no-member
        if not self._refreshAndPublish(): #pylint: disable=no-member
          gLogger.error("Can't refresh configuration from any source")


  @gen.coroutine
  def __run(self):
    """
      Trigger the autorefresh when configuration is expired
    """
    while self._automaticUpdate:
      yield gen.sleep(gConfigurationData.getPropagationTime())
      # Publish step is blocking so we have to run it in executor
      # If we are not doing it, when master try to ping we block the IOLoop
      yield IOLoop.current().run_in_executor(None, self.__AutoRefresh)

  @gen.coroutine
  def __AutoRefresh(self):
    """
      Auto refresh the configuration
      We disable pylint error because this class must be instanciated by a mixin to define the methods
    """
    if self._refreshEnabled: #pylint: disable=no-member
      if not self._refreshAndPublish(): #pylint: disable=no-member
        gLogger.error("Can't refresh configuration from any source")

  def daemonize(self):
    """ daemonize is probably not the best name because there is no daemon behind
    but we must keep it to the same interface of the DISET refresher """
    IOLoop.current().spawn_callback(self.__refreshLoop)
