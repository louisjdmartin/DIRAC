"""
  This class must be used ONLY by Refresher !

  It contains background activities for refresher, it works with IOLoop.

  To run Refresher with this class you have to set an Alternative Background Refresher
  in the refresher, use useAlternativeBackgroundRefresher() method for that

  WARNING: You can't use this class without IOLoop
            ==> If no IOLoop is started, methods can't be called
"""

from tornado import gen
from tornado.ioloop import IOLoop
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC import gLogger
import time

class RefresherIOLoop(object):

  def __init__(self):
    print "IOLOOP"
    #IOLoop.current().spawn_callback(self._refresh)
    pass

  @gen.coroutine
  def __run(self):
    while self._automaticUpdate:
      yield gen.sleep(gConfigurationData.getPropagationTime())
      # Publish step is blocking so we have to run it in executor
      # If we are not doing it, when master try to ping we have a deadlock
      yield IOLoop.current().run_in_executor(None, self.__AutoRefresh)

  @gen.coroutine
  def __AutoRefresh(self):
    if self._refreshEnabled:
      if not self._refreshAndPublish():
        gLogger.error("Can't refresh configuration from any source")

  def refreshConfigurationIfNeeded(self):
    """
      We kept it for interface but... we don't need to refresh
      because if we use this version it also mean that we using
      tornado who trigger the automatic refresh
    """
    if not self._refreshEnabled or self._automaticUpdate or not gConfigurationData.getServers():
      return
    if not self._lastRefreshExpired():
      return
    self._lastUpdateTime = time.time()
    self._refresh()
    return 

  def autoRefreshAndPublish(self, sURL):
    """
      Start the autorefresh background task

      :param str sURL: URL of the configuration server
    """
    print "autoRefreshAndPublish %s "%sURL
    gLogger.debug("Setting configuration refresh as automatic")
    if not gConfigurationData.getAutoPublish():
      gLogger.debug("Slave server won't auto publish itself")
    if not gConfigurationData.getName():
      import DIRAC
      DIRAC.abort(10, "Missing configuration name!")
    self._url = sURL
    self._automaticUpdate = True
    
    IOLoop.current().spawn_callback(self.__run)

  def daemonize(self):
    IOLoop.current().spawn_callback(self.__run)
