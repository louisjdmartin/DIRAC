"""
    Integratopm test to test if Tornado can run multiple services
"""


from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient



def test_service_user():
  service = TornadoClient('Framework/User')
  assert service.listUsers()['OK'] == True

def test_service_dummy():
  service = TornadoClient('Framework/DummyTornado')
  assert service.true()['OK'] == True