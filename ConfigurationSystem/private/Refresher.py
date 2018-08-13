""" Refresh local CS (if needed)
"""


__RCSID__ = "$Id$"

import time
import os

from DIRAC.ConfigurationSystem.private.RefresherThread import RefresherThread
from DIRAC.ConfigurationSystem.private.RefresherBase import RefresherBase




class Refresher(RefresherBase, RefresherThread):
  """
    The refresher
    A long time ago, in a code away, far away...
    A guy do the code to autorefresh the configuration
    To prepare transition to HTTPS we have done separation
    between the logic and the implementation of background
    tasks, it's the original version, for diset, using thread.

  """
  def __init__(self):
    RefresherThread.__init__(self)
    RefresherBase.__init__(self)




gRefresher = Refresher()



if __name__ == "__main__":
  time.sleep(0.1)
  gRefresher.daemonize()
