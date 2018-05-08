import csv
import matplotlib.pyplot as plt

testTornado = ['Tornado/results/results_2018.04.24_12.01.01']
testDirac = ['Dirac/results/results_2018.04.24_12.11.05']

def read_data(test, groupSize):
    with open(test+'/results.csv', 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')

        sumgrouptime = 0
        sumgrouprequestTime=0
        count = 0

        time=[]
        requestTime=[]

        for row in reader:
            count += 1
            sumgrouptime+=float(row[1])
            sumgrouprequestTime+=float(row[4])
            # Ici on moyenne un groupe de points sinon l'affichage est illisible
            if(count==groupSize):
                time.append(sumgrouptime/groupSize)
                requestTime.append(sumgrouprequestTime/groupSize)
                sumgrouptime=0
                sumgrouprequestTime=0
                count = 0
    return (time, requestTime)

def affiche(testTornado, testDirac, subplot, groupSize):
    plt.subplot(subplot)
    plt.ylabel('red = dirac')
   
    (timeTornado, requestTimeTornado) = read_data(testTornado,groupSize)
    (timeDirac, requestTimeDirac) = read_data(testDirac,groupSize)
   
    plt.plot(timeTornado,requestTimeTornado, 'b-',timeDirac,requestTimeDirac, 'r-')


# On suppose qu'il y a autant de test Tornado que Dirac pour ce script
# La formule bizarre permet juste d'afficher les graphiques dans la meme fenetre
for i in range(len(testTornado)):
    affiche(testTornado[i], testDirac[i], 100*len(testTornado)+11+i,10)
plt.show()
