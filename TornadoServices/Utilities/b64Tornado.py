"""
  Little utilities for tornado client and server to encode payload in base64
  It may be used by specificClients (like DIRAC.TornadoServices.Client.SpecificClient.ConfigurationClient)
"""


from base64 import b64encode, b64decode


def b64DictTostrDict(dictionnary):
  for key in dictionnary:
    if isinstance(dictionnary[key], basestring):
      dictionnary[key] = b64decode(dictionnary[key])
    elif isinstance(dictionnary[key], dict):
      dictionnary[key] = b64DictTostrDict(dictionnary[key])
  return dictionnary


def strDictTob64Dict(dictionnary):
  for key in dictionnary:
    if isinstance(dictionnary[key], basestring):
      dictionnary[key] = b64encode(dictionnary[key])
    elif isinstance(dictionnary[key], dict):
      dictionnary[key] = strDictTob64Dict(dictionnary[key])
  return dictionnary

def strListTob64List(listToEncode):
  encodedList = []
  for e in listToEncode:
    if isinstance(e, basestring):
      encodedList.append(b64encode(e))
    else:
      encodedList.append(e)
  return encodedList


def b64ListTostrList(listToEncode):
  encodedList = []
  for e in listToEncode:
    if isinstance(e, basestring):
      encodedList.append(b64decode(e))
    else:
      encodedList.append(e)
  return encodedList