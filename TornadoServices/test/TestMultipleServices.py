"""
    Test if same service work on DIRAC and TORNADO
    Testing if basic operation works
"""


from TornadoClient import TornadoClient



def test_service_user():
  service = TornadoClient('Framework/User')
  assert service.listUsers()['OK'] == True

def test_service_dummy():
  service = TornadoClient('Framework/Dummy')
  assert service.true()['OK'] == True