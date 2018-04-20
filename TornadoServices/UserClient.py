from time import time
from TornadoClient import RPCClient

service = RPCClient('Framework/User')

"""
Following are just exemple for calls
"""
def menu():
  print "1/ list users"
  print "2/ add user"
  print "3/ edit user"
  print "4/ exit"
  choice = raw_input()
  deb = time()
  if choice=='1':
    listUsers()
  elif choice=='2':
    addUser()
  elif choice=='3':
    editUser()
  elif choice=='4':
    return
  end = time()
  print "Request time: ", end-deb
  menu()

def listUsers():
  response = service.listUsers()
  if response['OK']:
    for i in response['Value']:
      print '#' + str(i[0]) + ':' + i[1]
  else:
    print 'ERROR:', response

def addUser():
  user = raw_input('Name: ')
  response = service.addUser(user)
  if not response['OK']:
    print 'ERROR:', response

def editUser():
  uid = raw_input('Id: ')
  user = raw_input('Name: ')
  response =  service.editUser(uid, user)
  if not response['OK']:
    print 'ERROR:', response

menu()