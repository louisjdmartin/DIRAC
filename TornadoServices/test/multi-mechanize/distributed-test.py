import xmlrpclib
import time
import csv
import matplotlib.pyplot as plt
import sys
### BEGIN OF CONFIGURATION ###

# Add all machine who have multimechanize client
serversList = ['137.138.150.194', 'server2'] 
# Each multimechanize client must listen the same ports, add the ports here
portList = ['9000','9001']

## END OF CONFIG

servers = []

print "Starting test servers...."
for port in portList:
  for server in serversList:
    servers.append(xmlrpclib.ServerProxy("http://%s:%s"(server,port)))
    servers[-1].run_test()
  time.sleep(2)


print "Waiting for results..."
while servers[-1].get_results() == 'Results Not Available':
  time.sleep(1)

try:
  output = sys.argv[1]
except KeyError
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