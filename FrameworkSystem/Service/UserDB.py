""" A test DB in DIRAC, using MySQL as backend
"""

from DIRAC.Core.Base.DB import DB

from DIRAC import gLogger, S_OK, S_ERROR


class UserDB(DB):
  """ Database system for users """

  def __init__(self):
    """
    Initialize the DB
    """
    DB.__init__(self, 'UserDB', 'Framework/UserDB', 10)
    retVal = self.__initializeDB()
    if not retVal['OK']:
      raise Exception("Can't create tables: %s" % retVal['Message'])

  def __initializeDB(self):
    """
    Create the tables
    """
    retVal = self._query("show tables")
    if not retVal['OK']:
      return retVal

    tablesInDB = [t[0] for t in retVal['Value']]
    tablesD = {}

    if 'user_mytable' not in tablesInDB:
      tablesD['user_mytable'] = {'Fields': {'Id': 'INTEGER NOT NULL AUTO_INCREMENT', 'Name': 'VARCHAR(64) NOT NULL'},
                                 'PrimaryKey': ['Id']
                                }

    return self._createTables(tablesD)

  def addUser(self, something):
    """ Add a user """
    gLogger.verbose("Insert " + something + " in DB")
    return self.insertFields('user_mytable', ['Name'], [something])

  def removeUser(self, uid):
    """ Remove a user """
    return self. _query('DELETE FROM user_mytable WHERE Id=' + str(uid))

  def editUser(self, uid, value):
    """ Edit a user """
    return self.updateFields('user_mytable', updateDict={'Name': value}, condDict={'Id': uid})

  def getUserName(self, uid):
    """ Get a user """
    user = self.getFields('user_mytable', condDict={'Id': uid})
    if len(user['Value']) == 1:
      return S_OK(user['Value'][0][1])
    return S_ERROR('USER NOT FOUND')

  def listUsers(self):
    return self._query('SELECT * FROM user_mytable')