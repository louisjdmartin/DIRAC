import threading
import thread
import time
import random
from DIRAC.ConfigurationSystem.Client.ConfigurationData import gConfigurationData
from DIRAC.ConfigurationSystem.Client.PathFinder import getGatewayURLs
from DIRAC.FrameworkSystem.Client.Logger import gLogger
from DIRAC.Core.Utilities import List, LockRing
from DIRAC.Core.Utilities.EventDispatcher import gEventDispatcher
from DIRAC.Core.Utilities.ReturnValues import S_OK, S_ERROR


class RefresherThread(threading.Thread):
  """
    All background task defined to use threads
  """
  def __init__(self):
    print "THREAD"
    threading.Thread.__init__(self)
    self._triggeredRefreshLock = LockRing.LockRing().getLock()


  def _refreshInThread(self):
    """
      Refreshing configration in the background. By default it use a thread but it can be 
      also runned in the IOLoop
    """
    retVal = self._refresh()
    if not retVal['OK']:
      gLogger.error("Error while updating the configuration", retVal['Message'])
  



  def refreshConfigurationIfNeeded(self):
    """
      Refresh the configuration if automatic update are disabled, refresher is enabled and servers are defined
    """
    if not self._refreshEnabled or self._automaticUpdate or not gConfigurationData.getServers():
      return
    self._triggeredRefreshLock.acquire()
    try:
      if not self._lastRefreshExpired():
        return
      self._lastUpdateTime = time.time()
    finally:
      try:
        self._triggeredRefreshLock.release()
      except thread.error:
        pass
    # Launch the refreshf
    thd = threading.Thread(target=self._refreshInThread)
    thd.setDaemon(1)
    thd.start()

  def autoRefreshAndPublish(self, sURL):
    """
      Start the autorefresh background task

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
    self.setDaemon(1)
    self.start()

  def run(self):
    while self._automaticUpdate:
      time.sleep(gConfigurationData.getPropagationTime())
      if self._refreshEnabled:
        if not self._refreshAndPublish():
          gLogger.error("Can't refresh configuration from any source")

  def daemonize(self):
    """
      Daemonize the background tasks
    """ 
    print "DAEMONIZE in refresherThread"
    
    self.setDaemon(1)
    self.start()