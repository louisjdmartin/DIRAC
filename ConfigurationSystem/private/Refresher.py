""" Refresh local CS (if needed)
"""


__RCSID__ = "$Id$"

import time
import os

from DIRAC.ConfigurationSystem.private.RefresherThread import RefresherThread
from DIRAC.ConfigurationSystem.private.RefresherBase import RefresherBase
from DIRAC.ConfigurationSystem.private.RefresherIOLoop import RefresherIOLoop




class Refresher(RefresherBase, RefresherThread):
  """
    The refresher!
  """
  def __init__(self):
    RefresherThread.__init__(self)
    RefresherBase.__init__(self)


class TornadoRefresher(RefresherBase, RefresherIOLoop):
  """
    The refresher, modified for Tornado
  """
  def __init__(self):
    RefresherIOLoop.__init__(self)
    RefresherBase.__init__(self)


if os.environ.get('USE_TORNADO_REFRESHER', 'NO') == 'YES':
  gRefresher = TornadoRefresher()
else:
  gRefresher = Refresher()



if __name__ == "__main__":
  time.sleep(0.1)
  gRefresher.daemonize()
