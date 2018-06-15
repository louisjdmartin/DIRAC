""" Dummy Service is a service for testing new dirac protocol
"""

__RCSID__ = "$Id$"

from DIRAC import S_OK
from DIRAC.Core.DISET.RequestHandler import RequestHandler
from DIRAC import gConfig

class diracCredDictHandler(RequestHandler):
  """ Dummy service for testing new DIRAC protocol (DISET -> HTTPS) """

  @classmethod
  def initializeHandler(cls, serviceInfo):
    """ Handler initialization
    """
    return S_OK()

  def initialize(self):
    """ Response initialization
    """
    pass


  auth_credDict = ['all']
  types_credDict = []
  def export_credDict(self):
    """ Add a user and return user id
    """
    c = self.srv_getRemoteCredentials()
    del c['x509Chain']
    return S_OK(c)