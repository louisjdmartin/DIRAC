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


class TornadoRefresher(RefresherBase, RefresherIOLoop):
  """
    The refresher, modified for Tornado
    It's the same refresher, the only thing who change is
    that we are using the IOLoop instead of threads for background 
    tasks, so it work with Tornado (HTTPS server).
  """
  def __init__(self):
    RefresherIOLoop.__init__(self)
    RefresherBase.__init__(self)



"""
  Here we define the refresher who should be used.
  By default we use the original refresher.

  Be careful, if you never start the IOLoop (with a TornadoServer for example)
  the TornadoRefresher will not work. IOLoop can be started after refresher
  but background tasks will be delayed until IOLoop start.
"""
if os.environ.get('USE_TORNADO_IOLOOP', 'false').lower() == 'true':
  gRefresher = TornadoRefresher()
else:
  gRefresher = Refresher()



if __name__ == "__main__":
  time.sleep(0.1)
  gRefresher.daemonize()
