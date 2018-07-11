""" Refresh local CS (if needed)
"""


__RCSID__ = "$Id$"

import time
import random
import os

from DIRAC.ConfigurationSystem.private.RefresherThread import RefresherThread
from DIRAC.ConfigurationSystem.private.RefresherBase import RefresherBase
from DIRAC.ConfigurationSystem.private.RefresherIOLoop import RefresherIOLoop




class Refresher(RefresherThread, RefresherBase):
  """
    The refresher!
  """
  def __init__(self):
    print "INIT REFRESHER"
    RefresherThread.__init__(self)
    RefresherBase.__init__(self)


class TornadoRefresher(RefresherIOLoop, RefresherBase):
  """
    The refresher!
  """
  def __init__(self):
    print "INIT REFRESHER"
    RefresherIOLoop.__init__(self)
    RefresherBase.__init__(self)


if os.environ.get('USE_TORNADO_REFRESHER', 'NO') == 'YES':
  gRefresher = TornadoRefresher()
else:
  gRefresher = Refresher()



if __name__ == "__main__":
  time.sleep(0.1)
  gRefresher.daemonize()
