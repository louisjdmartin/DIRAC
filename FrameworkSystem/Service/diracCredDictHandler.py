""" 
  Implementation of whoami in diset for tests
"""

__RCSID__ = "$Id$"

from DIRAC import S_OK, gLogger
from DIRAC.Core.DISET.RequestHandler import RequestHandler

class diracCredDictHandler(RequestHandler):
  """ Dummy service for testing new DIRAC protocol (DISET -> HTTPS) """

  @classmethod
  def initializeHandler(cls, infosDict):
    gLogger.warn("This service is for testing purpose, it may not be active in production")
    return S_OK()

  def initialize(self):
    gLogger.warn("This service is for testing purpose, it may not be active in production")


  auth_credDict = ['all']
  types_credDict = []
  def export_credDict(self):
    c = self.srv_getRemoteCredentials()
    del c['x509Chain'] #can't be serialized
    return S_OK(c)