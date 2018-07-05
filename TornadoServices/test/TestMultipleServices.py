"""
    Integration test to test if Tornado can run multiple services and client can find url.


    You must have 2 separate tornadohandlers and this services must be in dirac.cfg like normal service
    Only change: dips:// became https://  and Protocol = dips became Protocol = https
"""
from DIRAC.Core.Base.Script import parseCommandLine
parseCommandLine()

from DIRAC.TornadoServices.Client.TornadoClient import TornadoClient



def test_service_user():
  service = TornadoClient('Framework/User')
  assert service.ping()['OK'] == True

def test_service_dummy():
  service = TornadoClient('Framework/DummyTornado')
  assert service.ping()['OK'] == True