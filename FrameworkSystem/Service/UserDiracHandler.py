""" Dummy Service is a service for testing new dirac protocol
"""

__RCSID__ = "$Id$"

from DIRAC import S_OK
from DIRAC.Core.DISET.RequestHandler import RequestHandler
from DIRAC.FrameworkSystem.Service.UserDB import UserDB
from DIRAC import gConfig

class UserDiracHandler(RequestHandler):
  """ Dummy service for testing new DIRAC protocol (DISET -> HTTPS) """

  @classmethod
  def initializeHandler(cls, serviceInfo):
    """ Handler initialization
    """
    cls.userDB = UserDB()
    return S_OK()

  def initialize(self):
    """ Response initialization
    """



  auth_addUser = ['all']
  types_addUser = [basestring]
  def export_addUser(self, whom):
    """ Add a user and return user id
    """
    newUser = self.userDB.addUser(whom)
    if newUser['OK']:
      return S_OK(newUser['lastRowId'])
    return newUser

  auth_editUser = ['all']
  types_editUser = [int, basestring]
  def export_editUser(self, uid, value):
    """ Edit a user """
    return self.userDB.editUser(uid, value)

  auth_getUserName = ['all']
  types_getUserName = [int]
  def export_getUserName(self, uid):
    """ Get a user """
    return self.userDB.getUserName(uid)

  auth_listUsers = ['all']
  types_listUsers = []
  def export_listUsers(self):
    return self.userDB.listUsers()
