""" Dummy Service is a service for testing new dirac protocol
"""

__RCSID__ = "$Id$"

from DIRAC import S_OK
from DIRAC.Core.DISET.RequestHandler import RequestHandler
from DIRAC.Core.Base.UserDB import UserDB
class UserHandler(RequestHandler):
  """ Dummy service for testing new DIRAC protocol (DISET -> HTTPS) """

  @classmethod
  def initializeHandler(cls, serviceInfo):
    """ Handler initialization
    """
    return S_OK()

  def initialize(self):
    """ Response initialization
    """
    self.userDB = UserDB()



  auth_addUser = ['all']
  types_addUser = [basestring]
  def export_addUser(self, whom):
    """ Add a user and return user id
    """
    newUser = self.userDB.addUser(whom)
    if newUser['OK']:
      return S_OK(newUser['lastRowId'])
    return newUser


  auth_removeUser = ['all']
  types_removeUser = [int]
  def export_removeUser(self, uid):
    """ Remove a user """
    return self.userDB.removeUser(uid)

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
