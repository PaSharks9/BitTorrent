import bitstring
import os
import random
import string
import threading
import v4v6

# -------------------------------------Variabili Globali------------------------------------------------------
debug = False

trackerLock = threading.Lock()

sessionDict = {}  # { sessionId: (ip,port) }

# sharedDictFile= {md5: [fileName,lenFile,nPart,lenPart, downloadedMask, {sid1: masklist, sid2: masklist2, sid3: masklist3}], ..}
sharedFileDict = {}


# ------------------------------------------------------------------------------------------------------------

# Utilities Function

def buildFileMask(nPart):
    maskList = []
    resto = nPart % 8
    # Se il resto e > 0 allora  significa che una parte della maschera non sara composta da soli 1 ma da anche degli 0
    # Ricordando che il LSB e a sx la parte della maschera in cui ci saranno gli 0 parte sempre da sx
    if resto > 0:
        nMask = (nPart // 8) + 1
        restMask = []
        if nMask > 1:
            for index in range(nMask - 1):
                mask = []
                for i in range(8):
                    mask.append(1)
                maskList.append(mask)
            # Calcolo la parte della maschera che contiene il resto
            for index in range(resto):
                restMask.append(1)
            for index in range(8 - resto):
                restMask.append(0)
            maskList.append(restMask)
        else:
            # Calcolo la parte della maschera che contiene il resto
            for index in range(resto):
                restMask.append(1)
            for index in range(8 - resto):
                restMask.append(0)
            maskList.append(restMask)
    else:
        nMask = nPart // 8
        for index in range(nMask):
            mask = []
            for i in range(8):
                mask.append(1)
            maskList.append(mask)

    return maskList


def checkLogIn(sessionID):
    if sessionID in sessionDict:
        return True
    else:
        return False


def clear():
    if os.name == 'nt':  # Windows
        os.system('cls')
    else:  # Mac e Linux
        os.system('clear')


def idGenerator(size=16, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def recvExact(miaSocket, n_bytes):
    rimanenti = n_bytes
    letto = b""
    while True:
        temp = b""
        temp = miaSocket.recv(rimanenti)
        letto += temp

        if len(temp) == rimanenti:
            break  # ho finito di leggere
        else:
            rimanenti = rimanenti - len(temp)  # rimane qualcosa da leggere
    return letto


def printPeers():
    print("Logged Peers: ")
    index = 1
    if len(sessionDict) != 0:
        for sid in sessionDict:
            print(index, ") Sid:", sid, "Address: ", sessionDict[sid])
            index += 1
    print("-" * 107)


def printFiles():
    print("Shared Files: ")
    index = 1
    if len(sharedFileDict) != 0:
        for md5 in sharedFileDict:
            print(index, ") md5: ", md5)
            index += 1
    print("-" * 109)


def selectAction(Select, StartFlag, LoggedPeerFlag, SharedFileFlag):
    if StartFlag is False:
        if Select == "1":
            StartFlag = True
            try:
                trackerProxyServer = trackerProxyThread(PORT)
                trackerProxyServer.start()
            except:
                print("ERROR: Exception when creating a trackerProxyServer")

        else:
            print("Reloading the menu")

    else:
        if select == "2":
            LoggedPeerFlag = True
        elif select == "3":
            SharedFileFlag = True
        else:
            print("Reloading the menu")
    return StartFlag, LoggedPeerFlag, SharedFileFlag


# -------------------------------------------------------------------------------------------------------------
# Messages Function

def loginTracker(cIp, cPort):
    # Controllo se il peer e gia loggato
    for sessionId in sessionDict:
        if sessionDict[sessionId][0] == cIp and sessionDict[sessionId][1] == cPort:
            return "ALGI" + sessionId
    # Se siamo arrivati qui significa che il peer non era precedentemente gia loggato
    # Controllo che il SID generato non sia gia stato generato e associato ad un altro peer
    while True:
        try:
            sessionId = idGenerator()
        except:
            print("[loginTracker]: problem with idGenerator()")
            sessionId = "0000000000000000"
            return "ALGI" + sessionId
        if sessionId not in sessionDict:
            sessionDict[sessionId] = (cIp, cPort)
            return "ALGI" + sessionId


#            0        1      2      3            4                   5
# {md5: [fileName,lenFile,nPart,lenPart, downloadedMask, {sid1: masklist, sid2: masklist2, sid3: masklist3}], ..}
def logoutPeer(sid):
    partOwn = 0
    partDown = 0
    nLogFlag = False
    md5sShared = sharedFileDict.keys()
    for md5 in md5sShared:
        # Se il peer possiede delle parti del file md5 in considerazione (ciclo FOR)
        if sid in sharedFileDict[md5][5]:
            # Se si, prendo tutte le info del file in questione ( copia locale di valori )
            sharedFileInfo = sharedFileDict[md5]

            # Spacchetto le informazioni
            nPart = sharedFileInfo[2]  # n Parti
            sharingPeers = sharedFileInfo[5]  # quali peer condividono parti di questo file
            downloadedMask = sharedFileInfo[4]  # maschera del download del file md5 in questione
            maskList = sharingPeers[sid]    # maschera del peer riguardo a questo file md5
            print("len(maskList): ", str(len(maskList)))
            print("maskList: ", maskList)
            print("len(downloadedMask): ", str(len(downloadedMask)))
            print("downloadedMask: ", downloadedMask)
            countBit = 0
            # INDEX = ogni parte di cui e composto il file
            for index in range(len(downloadedMask)):
                # INDEXBIT = ogni bit della singola parte
                for indexBit in range(8):
                    if countBit <= int(nPart):
                        if maskList[index][indexBit] == 1:
                            partOwn += 1
                            # Se masklist con gli stessi indici e 1 , la relativa downloadedMask a quei indici deve per forza essere almeno a 1
                            if downloadedMask[index][indexBit] < 1:
                                nLogFlag = True
                            else:
                                # significa che altri l'hanno scaricato e questo peer puo aver fatto da sorgente
                                partDown += 1

                                downloadedMask[index][indexBit] = downloadedMask[index][indexBit] - 1
                        countBit += 1
                    else:
                        break
            
            if nLogFlag is False:
                sharedFileInfo[5].pop(sid)
            sharedFileInfo[4] = downloadedMask
            sharedFileDict.update({md5: sharedFileInfo})
    # Se nLogFlag e True significa che il file non e patrimonio del sistema e quindi il peer non si puo sloggare

    if nLogFlag is True:
        return "NLOG" + str(partDown).zfill(10)
    else:
        for key, value in sharedFileDict.items():
            if sid in value[4]:
                aggiornato = value
                aggiornato[4].pop(sid)
                sharedFileDict[key] = aggiornato

        sessionDict.pop(sid)
        return "ALOG" + str(partOwn).zfill(10)


#  {md5: [fileName,lenFile,nPart,lenPart, downloadMask, {sid1: masklist, sid2: masklist2, sid3: masklist3}], md5_2:(..)}
def trackerSearch1(searchString):
    returnList = []
    search = searchString.lower()
    search = search.strip()

    trackerLock.acquire()
    for md5 in sharedFileDict:
        fileName = sharedFileDict[md5][0].lower()
        fileName = fileName.strip()
        if search in fileName or search == '*':
            fileN = sharedFileDict[md5][0]
            lenFile = sharedFileDict[md5][1]
            lenPart = sharedFileDict[md5][3]
            newList = [md5, fileN, lenFile, lenPart]
            returnList.append(newList)
    trackerLock.release()

    nIdm5 = str(len(returnList))
    nIdm5 = nIdm5.zfill(3)

    msg = "ALOO" + nIdm5

    for element in returnList:
        md5 = element[0]
        fName = element[1]
        lFile = element[2]
        lPart = element[3]
        el = md5 + fName + lFile + lPart
        msg = msg + el

    return msg


# sessionDict =  { sessionId: (ip,port) }
#  {md5: [fileName,lenFile,nPart,lenPart, downloadMask,{sid1: masklist, sid2: masklist2, sid3: masklist3}], md5_2:(..)}
def trackerSearch2(md5):
    trackerLock.acquire()
    # sharedFileInfo = lista delle info relative all'md5 cercato.
    sharedFileInfo = sharedFileDict[md5]
    # sharingPeers = dizionario dei sid e delle relative maschere che condividono questo file o una sua parte
    sharingPeers = sharedFileInfo[5]
    # hitPeersList = lista di ip,port,mask relativa ad ogni peer che possiede parte del file o tutto il file
    hitPeersList = []
    for sid, mask in sharingPeers.items():
        ip = sessionDict[sid][0]
        port = sessionDict[sid][1]
        peer = [ip, port, mask]
        hitPeersList.append(peer)
    trackerLock.release()

    msg = ("AFCH" + str(len(sharingPeers)).zfill(3)).encode('utf-8')
    for element in hitPeersList:
        ip = element[0]
        port = element[1]
        b = ""
        for mask in element[2]:
            for bit in mask:
                b = b + str(bit)
        #partMsg = ip + port + b
        binaria = bitstring.BitArray(bin= b)
        partMsg = (ip + port).encode('utf-8') + binaria.bytes

        msg = msg + partMsg

    return msg


# sharedDictFile 0    1       2      3              4        5
# {md5: [fileName,lenFile,nPart,lenPart, downloadMask, {sid1: masklist, sid2: masklist2, sid3: masklist3}]..}
def updateFilePart(sid, md5, partNum):
    trackerLock.acquire()
    # Tiro fuori le info relative all'md5 in considerazione
    sharedFileInfo = sharedFileDict.pop(md5)

    # tiro fuori il dizionario dei peer che condividono una o piu parti di questo file ,
    # la downloadMask e il numero delle parti
    nPart = int(sharedFileInfo[2])
    downloadMask = sharedFileInfo[4]
    sharingPeers = sharedFileInfo[5]

    if partNum > nPart:
        if debug:
            print("[update]: Il partNum e maggiore delle nPart")
        return "APAD" + "-0000001"

    # Calcolo gli indici sulla maschera che rappresentano il partNum da aggiornare
    indexMask = (partNum // 8)
    bitIndex = (partNum % 8)

    # Se il sid non e presente, creo una maschera di 0 , l'associo al sid e l'aggiungo al dizionario
    if sid not in sharingPeers:
        # Il sid non e presente quindi vuol dire che questo file ha scaricato la prima parte del file
        newMask = []
        nPartMask = nPart // 8
        restMask = nPart % 8
        if restMask > 0:
            nPartMask += 1
        # Creo una maschera di soli zeri
        for index in range(nPartMask):
            newMask.append([0, 0, 0, 0, 0, 0, 0, 0])
        # Aggiungo tra gli sharingPeers del file la nuova maschera di 0 , sulla quale andro a settare la parte
        # che il peer mi ha indicato di aver scaricato,
        # in questo modo ho aggiornato i peers che possiedono parti di questo file
        sharingPeers.update({sid: newMask})

    # Prendo la maschera relativa al SID e aggiorno la sua parte
    maskList = sharingPeers[sid]
    print("indexMask: ", indexMask)
    print("bitIndex: ", bitIndex)
    print("len maskList: ", len(maskList))
    bit = maskList[indexMask][bitIndex]

     # if bit == 1:
        # return "APAD" + "-0000002"
    # else:
      #  maskList[indexMask - 1][bitIndex - 1] = 1
    maskList[indexMask][bitIndex] = 1
    sharingPeers.update({sid: maskList})

    # Ho scaricato una parte del file e devo aggiornare la maschera dei download per il logout
    print("[update] DownloadMask: ", downloadMask)
    downloadMask[indexMask][bitIndex] += 1

    # Una volta fatto l'update degli sharingPeers, devo reinserire la tupla modificata in sharedFileDict
    sharedFileInfo[4] = downloadMask
    sharedFileInfo[5] = sharingPeers
    sharedFileDict[md5] = sharedFileInfo

    # maskList a questo punto dovrebbe rappresentare la maschera modificata ,
    # quindi posso andare a fare il COUNT su questa variabile
    count = 0
    for partMask in maskList:
        partCount = partMask.count(1)
        count += partCount

    trackerLock.release()
    count = str(count).zfill(8)
    return "APAD" + count


# ------------------------------------------------------------------------------------------------------------
# Gestione Thread
class trackerProxyThread(threading.Thread):
    def __init__(self, p2pPort):
        threading.Thread.__init__(self)
        self.p2pPort = int(p2pPort)

    def run(self):
        sockP2p = v4v6.create_server_sock(("", self.p2pPort))
        # se il dispositivo su cui sto eseguendo la directory non supporta il "dual_stack" allora si crea una socket
        # multipla per coprire sia v4 che v6
        if not v4v6.has_dual_stack(sockP2p):
            sockP2p.close()
            sockP2p = v4v6.MultipleSocketsListener([("0.0.0.0", self.p2pPort), ("::", self.p2pPort)])

        # if debug is True:
        #   print("INFO: Proxy is waiting for connections.")

        while True:
            clientSock, clientAddress = sockP2p.accept()
            if debug is True:
                print("[trackerProxyThread]INFO: Received connection from: ", str(clientAddress))
            try:
                newThread = trackerServerThread(clientAddress, clientSock)
                newThread.start()
            except:
                print("[trackerProxyThread] ERROR: exception when trying to create a new trackerThread. "
                      "I'll close the socket received.")
                clientSock.close()


class trackerServerThread(threading.Thread):
    def __init__(self, clientAddress, clientSock):
        threading.Thread.__init__(self)
        # typeMessage e message non penso siano variabili d'istanza
        self.typeMessage = ""
        self.message = ""
        self.cAddress = clientAddress
        self.cSocket = clientSock
        self.cIp = ""
        self.cPort = ""
        self.sessionId = ""
        self.Logged = False

    def run(self):
        clear()
        if debug is True:
            print("[trackerServerThread] INFO: Created worker to serve: " + str(self.cAddress))

        # Come prima cosa del Run mi metto in ascolto aspettando un LOGI
        # CONTROLLARE I due WHILE self.Logged SE IN QUESTA CONFIGURAZIONE POSSONO FUNZIONARE
        while self.Logged is False:
            # Se sono qui significa che la socket e aperta e mi metto in ascolto
            self.typeMessage = recvExact(self.cSocket, 4).decode('utf-8')

            # Se nessun client e loggato su questo thread l'unica cosa che posso elaborare e una LOGI
            if self.typeMessage == "LOGI":
                # Ricezione messaggio e spacchettamento
                self.message = recvExact(self.cSocket, 60).decode('utf-8')
                self.cIp = self.message[0:55]
                self.cPort = self.message[55:]
                print("-" * 107)
                print("(", self.cAddress[0], ":", self.cAddress[1],
                      ")>" + self.typeMessage + self.cIp + ":" + self.cPort)

                # Calcolo SID
                trackerLock.acquire()
                responseLOGI = loginTracker(self.cIp, self.cPort)
                trackerLock.release()

                # Tiro fuori il SID, lo assegno alla sessione corrente e setto il flag di login
                self.sessionId = responseLOGI[4:]
                if self.sessionId != "0000000000000000":
                    self.Logged = True
                else:
                    print("[trackerServerThread]LOGI: The SID returned is '0000000000000000'. "
                          "Some errors are occurred in LOGI process.\n Please, retry to log-in")
                    continue
                # Invio risposta
                try:
                    self.cSocket.sendall(responseLOGI.encode('utf-8'))
                    print("(", self.cAddress[0], ":", self.cAddress[1], ")<" + responseLOGI)
                    print("-" * 107)
                except:
                    print("[trackerServerThread]LOGI: Error in sending responseLogi")
                clear()
            else:
                print("[trackerServerThread]The user is not logged. To perform any request, the user must be logged")
                print("-" * 107)
                continue

            # Se ho effettuato correttamente il LogIn allora entro in ascolto con un loop,
            # altrimenti mi rimetto in ascolto aspettando una LOGI
            while self.Logged is True:
                # il thread si mette in ascolto sulla socket
                self.typeMessage = recvExact(self.cSocket, 4).decode('utf-8')

                if self.typeMessage == "LOGI":
                    cIp = self.message[0:55]
                    cPort = self.message[55:]
                    print("-" * 107)
                    print("(", cIp, ")>" + self.message)
                    print("The address ", cIp + ":", cPort, "is already logged with SID = ", self.sessionId)

                    # ritorno il SID e mi rimetto quindi in ascolto sulla socket
                    msg = "ALGI" + self.sessionId
                    try:
                        self.cSocket.sendall(msg.encode('utf-8'))
                        print("(", cIp, ")<" + msg)
                        print("-" * 107)
                    except:
                        print("[trackerServerThread]Error in sendall in inner Logi")
                        print("-" * 107)
                    continue

                # Se il typeMessage non e una LOGI allora processo finalmente la richiesta
                # Tiro fuori il SID per effettuare il controllo sul login.
                # Teoricamente in questo ciclo non si puo entrare se il peer non e loggato,
                # il controllo lo faccio comunque per sicurezza
                sid = recvExact(self.cSocket, 16).decode('utf-8')

                trackerLock.acquire()
                if checkLogIn(sid) is True:
                    trackerLock.release()
                    if self.typeMessage == "ADDR":
                        # Ricezione messaggio
                        self.message = recvExact(self.cSocket, 148).decode('utf-8')
                        clear()
                        print("-" * 107)
                        print("(", self.cAddress[0], ":", self.cAddress[1],
                              ")>" + self.typeMessage + sid + self.message)

                        # Spacchettamento del messaggio ricevuto
                        lenFile = int(self.message[0:10])
                        lenPart = int(self.message[10:16])
                        fileName = self.message[16:116]
                        md5 = self.message[116:]

                        # Calcolo il numero di parti in cui viene suddiviso il file
                        if (lenFile % lenPart) > 0:
                            nPart = str((lenFile // lenPart) + 1)
                        else:
                            nPart = str(lenFile // lenPart)

                        # Riporto la lenFile, la lenPart e la nPart in un formato stringa e nella giusta dimensione di B
                        nPart = nPart.zfill(8)
                        lFile = str(lenFile).zfill(10)
                        lPart = str(lenPart).zfill(6)

                        # Voglio aggiungere un file, quindi per forza se l'aggiungo ho tutte le parti e quindi creo una
                        # masklist composta da soli 1
                        maskList = buildFileMask(int(nPart))

                        # sharedDictFile= {md5: [fileName,lenFile,nPart,lenPart, downloadMask, {sid1: masklist, sid2: masklist2, sid3: masklist3}], md5_2:(..)}
                        # Controllo se il file e gia presente nel dizionario
                        trackerLock.acquire()
                        if md5 in sharedFileDict:
                            print("The file you want to add is already present. Updating the information..")
                            fileTuple = sharedFileDict.pop(md5)
                            if lPart != fileTuple[3]:
                                print("[trackerServerThread]Updating File Info: Once added, "
                                      "the length of the parts of the file cannot be changed")
                            fileTuple[0] = fileName
                            sharedFileDict[md5] = fileTuple
                        else:
                            # Creo una nuova tupla con i nuovi dati
                            # se l'md5 non e presente nel dizionario inserisco direttamente newTuple nel dizionario
                            downloadMask = []
                            restDMask = int(nPart) % 8
                            if restDMask > 0:
                                partDMask = (int(nPart) // 8) + 1
                            else:
                                partDMask = int(nPart) // 8
                            for index in range(partDMask):
                                downloadMask.append([0, 0, 0, 0, 0, 0, 0, 0])
                            newTuple = [fileName, lFile, nPart, lPart, downloadMask, {sid: maskList}]
                            sharedFileDict[md5] = newTuple
                        trackerLock.release()

                        # Costruzione e invio del messaggio
                        responseADDR = "AADR" + nPart
                        try:
                            self.cSocket.sendall(responseADDR.encode('utf-8'))
                            print("(", self.cAddress[0], ":", self.cAddress[1], ")<" + responseADDR)
                            print("-" * 107)
                        except:
                            print("[trackerServerThread] Error in sending responseADDR")
                            print("-" * 107)
                    # Ricerca , Fase 1
                    elif self.typeMessage == "LOOK":
                        # Ricezione messaggio
                        self.message = recvExact(self.cSocket, 20).decode('utf-8')
                        clear()
                        print("-" * 107)
                        print("(", self.cAddress[0], ")>" + self.typeMessage + self.message)

                        # Spacchettamento messaggio
                        searchString = self.message[0:]

                        # Effettuo Fase 1 della ricerca
                        responseLOOK = trackerSearch1(searchString)

                        # Invio risultati al peer
                        try:
                            self.cSocket.sendall(responseLOOK.encode('utf-8'))
                            print("(", self.cAddress[0], ")<" + responseLOOK)
                            print("-" * 107)
                        except:
                            print("[trackerServerThread] Error in LOOK Socket sendall")
                            print("-" * 107)
                    # Ricerca, Fase 2
                    elif self.typeMessage == "FCHU":
                        # Ricezione messaggio
                        md5 = recvExact(self.cSocket, 32).decode('utf-8')
                        print("(", self.cAddress[0], ")>", self.typeMessage, sid, md5)
                        # Ricerca delle parti
                        responseAFCH = trackerSearch2(md5)

                        try:
                            self.cSocket.sendall(responseAFCH)
                            print("(", self.cAddress[0], ")<", responseAFCH)
                            print("-" * 107)
                        except:
                            print("[trackerServerThread] Error in FCHU Socket sendall")
                            print("-" * 107)
                    elif self.typeMessage == "RPAD":
                        # Ricezione Messaggio e spacchettamento
                        self.message = recvExact(self.cSocket, 40).decode('utf-8')
                        md5 = self.message[0:32]
                        partNum = int(self.message[32:])  # [8B]
                        print("-" * 107)
                        print("(", self.cAddress[0], ")>" + self.typeMessage + self.message)

                        # Modifico la maschera relativa a questo file e ritorno il n di parti possedute dal peer
                        responseAPAD = updateFilePart(sid, md5, partNum)

                        if responseAPAD[4:] == "-0000001":
                            print("[updateFilePart] Error: the part of file that the peer has downloaded "
                                  "exceed the number of the total parts of the file:", md5)
                        elif responseAPAD[4:] == "-0000002":
                            print("[updateFilePart] Warning: the part of the file was already downloaded by the peer")
                        try:
                            self.cSocket.sendall(responseAPAD.encode('utf-8'))
                            print("(", self.cAddress[0], ")<" + responseAPAD)
                            print("-" * 107)
                        except:
                            print("[trackerServerThread] Error in RPAD Socket sendall")
                            print("-" * 107)
                    elif self.typeMessage == "LOGO":
                        print("-" * 107)
                        print("(", self.cAddress[0], ")>" + self.typeMessage + sid)
                        trackerLock.acquire()
                        responseLOGO = logoutPeer(sid)
                        trackerLock.release()
                        if responseLOGO[0:4] == "NLOG":
                            print("[LOGO] The peer:", sid, "  wants to disconnect but still has files "
                                                           "that have not yet been shared")
                        elif responseLOGO[0:4] == "ALOG":
                            print("Disconnecting..")
                        try:
                            self.cSocket.sendall(responseLOGO.encode("utf-8"))
                            print("(", self.cAddress[0], ":", self.cAddress[1], ")<" + responseLOGO)
                            print("-" * 107)
                            # self.cSocket.shutdown()
                            # self.cSocket.close()
                        except:
                            print("[trackerServerThread] Error in LOGO socket sendall")
                            print("-" * 107)
                else:
                    trackerLock.release()
                    print("[trackerServerThread] Error: the user is not logged, to perform", self.typeMessage,
                          "action, the user must be logged")
                    print("-" * 107)


# ------------------------------------------------------ MAIN ---------------------------------------------------------
if debug is True:
    PORT = "3000"
else:
    PORT = input("Insert the port of the Tracker: ")
startFlag = False
loggedPeerFlag = False
sharedFileFlag = False
completeFlag = False
while True:

    if loggedPeerFlag is True and sharedFileFlag is True and startFlag is True:
        completeFlag = True

    # Stampe Dati
    clear()
    print("-" * 50, "TRACKER", "-" * 50)
    if startFlag is True:
        print("Status: OnLine")
    else:
        print("Status: OffLine")
    print("-" * 109)
    if loggedPeerFlag is True:
        printPeers()
    if sharedFileFlag is True:
        printFiles()

    # Gestione Scelte e Menu
    if startFlag is True:
        if completeFlag is not True:
            print("Menu: ")
            if loggedPeerFlag is not True:
                print("1) Stamp logged Peers")
            if sharedFileFlag is not True:
                if loggedPeerFlag is True:
                    print("1) Stamp shared Files")
                elif loggedPeerFlag is not True:
                    print("2) Stamp shared files")
            select = input("Select the action to perform (press any key to reload the menu):")
            if select == "":
                select = "100"
            select = int(select)
            if loggedPeerFlag is True:
                select = str(select + 2)
            elif loggedPeerFlag is not True:
                select = str(select + 1)
            startFlag, loggedPeerFlag, sharedFileFlag = selectAction(select, startFlag, loggedPeerFlag, sharedFileFlag)
        else:
            print("-" * 48 + " Activities " + "-" * 49)
            input("Press any key to reload the activities")
    else:
        print("Menu:")
        print("1) Start the Tracker")
        select = input("Select the action to perform (press any key to reload the menu):")
        startFlag, loggedPeerFlag, sharedFileFlag = selectAction(select, startFlag, loggedPeerFlag, sharedFileFlag)
