from DIRAC.FrameworkSystem.Service.UserDB import UserDB
from DIRAC import S_OK

class UserHandler:
  def __init__(self):
    self.userDB = UserDB()

  def addUser(self, whom):
    """ Add a user and return user id
    """
    newUser = self.userDB.addUser(whom)
    if newUser['OK']:
      return S_OK(newUser['lastRowId'])
    return newUser

  def removeUser(self, uid):
    """ Remove a user """
    return self.userDB.removeUser(uid)

  def editUser(self, uid, value):
    """ Edit a user """
    return self.userDB.editUser(uid, value)

  def getUserName(self, uid):
    """ Get a user """
    return self.userDB.getUserName(uid)

  def listUsers(self):
    return self.userDB.listUsers()
