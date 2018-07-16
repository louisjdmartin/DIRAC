"""
  This class must be used ONLY by Refresher !

  It contains background activities for refresher, it works with IOLoop.

  To run Refresher with this class you have to set an Alternative Background Refresher
  in the refresher, use useAlternativeBackgroundRefresher() method for that

  WARNING: You can't use this class without IOLoop
            ==> If no IOLoop is started, methods can't be called
"""

import time

from tornado import gen
from tornado.ioloop import IOLoop

from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC import gLogger


class RefresherIOLoop(object):
  """
    Refresher adapted to work with Tornado had its IOLoop
  """

 

  def refreshConfigurationIfNeeded(self):
    """
      We kept it for interface but... we don't need to refresh
      because if we use this version it also mean that we using
      tornado who trigger the automatic refresh

      We disable pylint error because this class must be instanciated by a mixin to define the methods
    """
    if not self._refreshEnabled or self._automaticUpdate or not gConfigurationData.getServers(): #pylint: disable=no-member
      return
    if not self._lastRefreshExpired(): #pylint: disable=no-member
      return
    self._lastUpdateTime = time.time()
    self._refresh() #pylint: disable=no-member
    return

  def autoRefreshAndPublish(self, sURL):
    """
      Start the autorefresh background task

      :param str sURL: URL of the configuration server
    """
    print "autoRefreshAndPublish %s " % sURL
    gLogger.debug("Setting configuration refresh as automatic")
    if not gConfigurationData.getAutoPublish():
      gLogger.debug("Slave server won't auto publish itself")
    if not gConfigurationData.getName():
      import DIRAC
      DIRAC.abort(10, "Missing configuration name!")
    self._url = sURL
    self._automaticUpdate = True

    IOLoop.current().spawn_callback(self.__run)

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
    IOLoop.current().spawn_callback(self.__run)
