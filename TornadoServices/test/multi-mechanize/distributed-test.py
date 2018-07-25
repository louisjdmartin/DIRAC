import xmlrpclib
import time
import csv
import matplotlib.pyplot as plt

# We define the list of multimechanize servers...
serversList = ['http://137.138.150.194:9000', 'http://137.138.150.194:9002', 'http://137.138.150.194:9003', 'http://137.138.150.194:9004', 'http://137.138.150.194:9005', 'http://137.138.150.194:9006', 'http://137.138.150.194:9007', 'http://137.138.150.194:9008'] 

servers = []

print "Starting test servers...."
for server in serversList:
  servers.append(xmlrpclib.ServerProxy(server))
  time.sleep(2)
  servers[-1].run_test()


print "Waiting for results..."
while servers[-1].get_results() == 'Results Not Available':
  time.sleep(1)

output = str(time.time())
fileCount = 0
for server in servers:
  fileCount += 1
  fileName = "%s.%s.txt"%(output, fileCount)
  print "Writing output file %s" % fileName
  file = open(fileName, 'w')
  file.write(server.get_results())
  file.close()

print "python plot-distributedTest.py %s %d" % (output, fileCount)