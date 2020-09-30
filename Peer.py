#!/usr/bin/env python3

############################################ LIBRERIE ############################################
import bitstring
import hashlib
import ipaddress
import os
import random
import socket
import sys
import threading
import time
import v4v6

############################################ VARIABILI ############################################
debug = False  # Consente di aumentare (True) / ridurre (False) la quantità di output prodotto a video

script_dir = os.path.dirname(__file__)  # E' il path dove si trova questo script  

config = {}
# Dizionario in cui salviamo tutti i parametri inseriti all'avvio:
#   peer_ipv4       ipv4 (in formato compresso) del peer
#   peer_ipv6       ipv6 (in formato compresso) del peer
#   peer_port       porta P2P (in formato stringa di 5 caratteri) a cui altri peer possono contattarmi
#   tracker_ipv4    ipv4 (in formato compresso) del tracker
#   tracker_ipv6    ipv6 (in formato compresso) del tracker
#   tracker_port    porta (in formato stringa di 5 caratteri) a cui risponde il tracker

inUseDict = {}
# Dizionario che conterrà una maschera delle parti in condivisione per i soli file NON COMPLETATI,
# Esempio:
#   inUseDict[md5] = (-1,-1,0,5,0,3)
#   - parti 0 ed 1 sono le uniche che mi mancano
#   - parti 2 e 4 sono presenti e non le sto inviando a nessuno
#   - parti 3 e 5 sono presenti e le sto inviando a qualcuno (a 5 peer la parte 3 ed a 3 peer la parte 5)

sharedDict = {}
# Dizionario dei file che il PEER ha posto in condivisione (serve per la RETR) così
#  da poter leggere il file
# sharedDict = {md5: (abs_file_path, n_parts, len_part, (parts_mask))}

sid = ""  # Finché saremo loggati quì troveremo il session_id restituitoci dal tracker

logged = False  # Questo flag ci permette di sapere in qualsiasi istante se siamo loggati (True) oppure no (False)

sTracker = None  # Quì finirà la socket che ci porrà in collegamento col tracker (dal login al logout)

lockUseDict = threading.Lock()  # lock da acquisire per poter accedere in sicurezza a "inUseDict"

lockSharedDict = threading.Lock()  # lock da acquisire per poter accedere in sicurezza a "sharedDict"

lockSocket = threading.Lock()  # lock da acquisire per poter usare correttamente la socket con il tracker

sending = 0  # questo contatore ci permette di sapere, in qualsiasi momento, quanti peer stiamo servendo
lockSending = threading.Lock()  # lock da acquisire per poter modificare correttamente la variabile "sending"

partsList = []  # questa lista, durante un download, viene aggiornata ogni 60 secondi da un "partsUpdated" e viene consultata


# dal thread principale per scegliere, di volta in volta, la prossima parte da scaricare.

############################################# CLASSI #############################################
class webTalker(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.killed = False
        self.webHost = '127.0.0.1'  # Accetto solo connessioni da localhost (modificandolo è possibile agganciarsi ad una macchina distinta
        self.webPort = 3001  # La porta sarà incrementata fino a trovare la prima libera
        self.webSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.webConnection = None
        self.webAddress = None

        # Trovo una porta libera
        while (self.webPort < 65636):
            try:
                self.webSocket.bind((self.webHost, self.webPort))
                break
            except:
                self.webPort = self.webPort + 1

        self.webSocket.listen(1)  # Mi pongo in ascolto
        print("INFO: Please connect the WebInterface to the port ", self.webPort)
        self.webAddress = None
        self.sTracker = None
        self.config = {}
        self.peerProxy = None
        self.logged = False

        self.webConnection, self.webAddress = self.webSocket.accept()  # Aspetto che l'interfaccia web si connetta
        self.webSocket.close()

    def run(self):
        while self.killed is False:
            data = recvExact(self.webConnection,
                             4)  # Ho assunto che i comandi inviati dall'interfaccia web siano lunghi 4 bytes
            data = data.decode('utf-8')
            print("Ricevuto dal web comando: ", data)
            if data == "GETP":
                self.config = loadConfiguration()
                if self.config is None:
                    data = ""
                else:
                    data = ""
                    data = data + str(self.config["peer_ipv4"]) + ','
                    data = data + str(self.config["peer_ipv6"]) + ','
                    data = data + str(self.config["peer_port"]) + ','
                    data = data + str(self.config["tracker_ipv4"]) + ','
                    data = data + str(self.config["tracker_ipv6"]) + ','
                    data = data + str(self.config["tracker_port"])

            elif data == "SETP":
                data = recvUntil(self.webConnection, '%').decode('utf-8')
                lista = data.split(',')
                if lista[0] != "":
                    self.config["peer_ipv4"] = str(implodeIpv4(lista[0]))
                if lista[1] != "":
                    self.config["peer_ipv6"] = str(implodeIpv6(lista[1]))
                if lista[2] != "":
                    self.config["peer_port"] = str(lista[2]).zfill(5)
                if lista[3] != "":
                    self.config["tracker_ipv4"] = str(implodeIpv4(lista[3]))
                if lista[4] != "":
                    self.config["tracker_ipv6"] = str(implodeIpv6(lista[4]))
                if lista[5] != "":
                    self.config["tracker_port"] = str(lista[5]).zfill(5)

                # Sistemo IPS
                self.config["peer_ips"] = str(explodeIpv4(self.config["peer_ipv4"])) + '|' + str(
                    explodeIpv6(self.config["peer_ipv6"]))
                self.config["tracker_ips"] = str(explodeIpv4(self.config["tracker_ipv4"])) + '|' + str(
                    explodeIpv6(self.config["tracker_ipv6"]))

                saveConfiguration(self.config)
                data = "SAVD"

            elif (data == "UPLD"):
                data = recvUntil(self.webConnection, '%').decode('utf-8')
                lista = data.split(',')
                data = addFile(self.sTracker, sid, lockSocket, sharedDict, lista[0], lista[1], self.config)

            elif (data == "LOGI"):
                if (self.sTracker is None):
                    tracker_ips = str(self.config["tracker_ipv4"]) + '|' + str(self.config["tracker_ipv6"])
                    self.sTracker = randomConnection(tracker_ips, int(self.config["tracker_port"]))

                sid = login(self.sTracker, lockSocket, self.config)

                if sid != "0000000000000000":
                    self.logged = True
                    self.peerProxy = istanziaPeerProxy(self.config)
                    self.peerProxy.enable()
                    data = str(sid)
                else:
                    data = "ERR"

            elif data == "LOG?":
                if self.logged is True:
                    data = sid
                else:
                    data = "False"

            elif data == "LOGO":
                esito = logout(self.sTracker, sid, lockSocket, self.peerProxy)
                if esito is True:  # Logout concesso dal tracker
                    self.logged = False
                    self.sTracker = None
                    sid = ""
                    lockSharedDict.acquire()
                    sharedDict.clear()
                    lockSharedDict.release()
                    data = "OK"
                else:
                    data = "KO"

            elif data == "HOME":
                data = ""
                # md5:lenparts:ownedparts:totalparts
                if len(sharedDict.items()) != 0:
                    for md5, tupla in sharedDict.items():
                        presenti = tupla[3].count('1')
                        data = (str(md5) + ":" + str(tupla[1]).ljust(6, ' ') + ":" + str(
                            presenti) + ":" + str(tupla[2]))
                        data += "|"
            elif data == "FIND":
                data = recvExact(self.webConnection,
                                 20)  # Leggo la chiave da ricercare (già formattata a 20 caratteri da WebUI)
                data = data.decode('utf-8')
                print("RICEVUTO DAL WEB:" + data)
                risultati = searchFile(self.sTracker, sid, lockSocket, data)

                data = ""
                if risultati is not None:  # Se ci sono risultati converto la lista in formato CSV
                    for index in range(0, len(risultati)):
                        data = data + risultati[index][0] + ','
                        data = data + risultati[index][1] + ','
                        data = data + str(risultati[index][2]) + ','
                        data = data + str(risultati[index][3]) + ','

                risultati = searchFile(self.sTracker, sid, lockSocket, data)

                data = ""
                if risultati is not None:  # Se ci sono risultati converto la lista in formato CSV
                    for index in range(0, len(risultati)):
                        data = data + risultati[index][0] + ','
                        data = data + risultati[index][1] + ','
                        data = data + str(risultati[index][2]) + ','
                        data = data + str(risultati[index][3]) + ','

            elif data == "DOWN":
                data = recvUntil(self.webConnection, '%')
                data = data.decode('utf-8')
                result = data.split(',')
                data = downloadFile(result, sid, self.sTracker, lockSocket)

            data = data + "%"  # Uso il simbolo % come terminatore del messaggio (dall'altra parte leggerò finché non
            # lo trovo)
            self.webConnection.sendall(data.encode('utf-8'))

        try:
            self.webConnection.close(socket.SHUT_RDWR)
            self.webAddress = None
        except:
            print("WARNING: Some exception when trying to close the connection to the WebInterface.")

    def kill(self):
        self.killed = True


class partsUpdater(threading.Thread):
    def __init__(self, md5, Session_ID, n_parts, socket_tracker, parts_lock, socket_lock):
        threading.Thread.__init__(self)
        self.completed = False
        self.n_parts = n_parts
        self.sTracker = socket_tracker
        self.md5 = md5
        self.sid = Session_ID
        self.lock = parts_lock
        self.sLock = socket_lock

    def run(self):
        while (self.completed is False):
            peerList = checkStatus(self.sid, self.md5, self.n_parts, self.sTracker, self.sLock)
            temp = []
            for i in range(0, self.n_parts):
                temp.append((i, 0, []))  # la lista conterrà (id_parte, #peer_che_la_possiedono, ((ip1,p1), (ip2,p2)))

            for peer in peerList:
                for part in range(0, self.n_parts):
                    if (peer[2][part] == '1'):
                        tupla = (peer[0], peer[1])

                        if (temp[part][2] == []):
                            temp[part] = (temp[part][0], temp[part][1] + 1, [tupla])
                        else:
                            # lista = temp[part][2].copy()
                            lista = temp[part][2]
                            lista.append(tupla)
                            temp[part] = (temp[part][0], temp[part][1] + 1, lista)
                            # temp[part] = (temp[part][0], temp[part][1] +1, (temp[part][2]).append(tupla))

                        # temp[part] = (temp[part][0], temp[part][1] +1, (temp[part][2]).append(tupla))
                        # id_parte  ,copie_disponibili, lista dei peer che hanno questa parte (ips,port)

                    # if(peer[2][part] == '1'):
                    #    if(temp[part][1] == 0):
                    #        temp[part] = (temp[part][0], temp[part][1] +1, peer)
                    #    elif(temp[part][1] == 1):
                    #        tuple = (temp[part][2], peer)
                    #        temp[part] = (temp[part][0], temp[part][1] +1, tuple)
                    #    else:
                    #        tuple = temp[part][2].append(peer)
                    #        temp[part] = (temp[part][0], temp[part][1] +1, tuple)

            temp.sort(reverse=False, key=ordinamento)  # ordino la lista delle parti dalla più rara alla più disponibile
            self.lock.acquire()
            # aggiorno la lista che gli altri processi consultano
            global partsList
            partsList = temp

            # partsList.clear()
            # for el in temp:
            #    partsList.append(el)
            self.lock.release()

            # print("NEW - PARTSLIST")    #DEBUG
            # for el in temp:             #DEBUG
            #    print(el)               #DEBUG

            time.sleep(60)

    def stop(self):
        self.completed = True


class peerWorker(threading.Thread):
    def __init__(self, clientAddress, clientSock):
        threading.Thread.__init__(self)
        self.cAddress = clientAddress
        self.cSocket = clientSock

    def run(self):
        if (debug is True): print("[PEER_WORKER] Created thread to serve: " + str(self.cAddress))

        message = recvExact(self.cSocket, 4).decode('utf-8')  # ricevo il comando (gestisco solo RETP)
        if (message != "RETP"):
            print("[PEER_WORKER] WARNING: Received an unknown command " + str(message) + ". Abort.")
            self.cSocket.close()
            return

        message += recvExact(self.cSocket, 40).decode('utf-8')  # ricevo File_md5[32B].PartNum[8B]
        print("[PEER_WORKER] >" + str(message))

        file_md5 = message[4:36]
        part_id = message[36:]

        lockSharedDict.acquire()

        if (file_md5 not in sharedDict):
            lockSharedDict.release()
            print("[PEER_WORKER] WARNING: Requested file with MD5=" + str(
                file_md5) + " but i've not found inside SharedDict. Abort.")
            self.cSocket.close()
            return

        file_name = sharedDict[file_md5][0]
        file_lenParts = int(sharedDict[file_md5][1])
        file_nParts = int(sharedDict[file_md5][2])
        file_mask = sharedDict[file_md5][3]

        # Controllo la correttezza di "part_id"
        if (int(part_id) not in range(0, file_nParts)):
            print("[PEER_WORKER] WARNING: Requested part=" + str(part_id) + " but that file has " + str(
                file_nParts) + ". Abort.")
            lockSharedDict.release()
            self.cSocket.close()
            return

        # Controllo di avere la parte richiesta
        if (file_mask[int(part_id)] == '0'):
            print("[PEER_WORKER] ERROR: Requested the part=" + str(part_id) + " of md5=" + str(
                file_md5) + " but i don't have that part. Abort.")
            lockSharedDict.release()
            self.cSocket.close()
            return

        lockSharedDict.release()

        # segnalo che sto gestendo una richiesta (legittima) di un peer
        updateSending(1)

        # controllo se ho tutto il file (quindi un unico file in cui cercare la parte all'interno, oppure ho il file della parte)
        if ('0' in file_mask):
            parziale = True

            while True:
                if (partAcquire(file_md5, part_id) is True):
                    break

            part_name = file_md5 + '.' + str(part_id).zfill(8)
            try:
                mioFile = open(os.path.join(script_dir, part_name), "rb")
            except:
                print("[PEER_WORKER] ERROR: PartFile (" + str(part_name) + ") not found. Abort.")
                self.cSocket.close()
                partRelease(file_md5, part_id)
                return

            partData = mioFile.read(file_lenParts)
            mioFile.close()
            partRelease(file_md5, part_id)

        else:
            parziale = False
            try:
                mioFile = open(os.path.join(script_dir, file_name), "rb")
            except:
                print("[PEER_WORKER] ERROR: File (" + str(file_name) + ") not found. Abort.")
                self.cSocket.close()
                return
            offset = int(part_id) * file_lenParts
            mioFile.seek(offset)  # mi sposto all'inizio della parte
            partData = mioFile.read(file_lenParts)
            mioFile.close()

        # Suddivisione file in chunk
        partSize = len(partData)
        data_offset = 0

        # chunkMin = (partSize // 99999) + 1
        lenghtMin = (partSize // 99999999) + 1
        while True:
            lenChunk = random.randrange(lenghtMin, min(100000, partSize))
            nChunk = partSize // lenChunk

            residuo = partSize - nChunk * lenChunk
            if (residuo > 0):
                nChunk += 1

            if (residuo < 100000):
                break
            # nChunk = random.randrange(chunkMin, min(100000, partSize))
            # lenChunk = partSize // nChunk

            # if partSize - (nChunk * lenChunk) < 100000:  # controllo che l'ultimo chunk non ecceda i 100Kb
            #    break

        print("[PEER_WORKER] INFO: Part splitted in " + str(nChunk) + " chunks.")
        print("Part size:\t" + str(partSize))
        print("Chunk number:\t" + str(nChunk))
        print("Chunk size:\t" + str(lenChunk))

        message = "AREP" + str(nChunk).zfill(6)
        print("[PEER_WORKER] <" + str(message))
        try:
            self.cSocket.send(message.encode('utf-8'))
        except:
            print("[PEER_WORKER] Unable to send AREP. Abort.")
            self.cSocket.close()
            return

        for i in range(nChunk):
            if i == (nChunk - 1):  # se è l'ultimo chunk ne calcolo la sua dimensione
                lenChunk = partSize - data_offset
                dataChunk = str(lenChunk).zfill(5).encode('utf-8')
                dataChunk += (partData[data_offset:])
            else:
                dataChunk = str(lenChunk).zfill(5).encode('utf-8')
                dataChunk += (partData[data_offset: (data_offset + lenChunk)])

            data_offset += lenChunk
            self.cSocket.sendall(dataChunk)

        self.cSocket.shutdown(socket.SHUT_RDWR)
        self.cSocket.close()
        print("[PEER_WORKER] INFO: Part" + str(part_id) + " of MD5(" + str(file_md5) + ") successfully sent!")

        # segnalo che ho un peer in meno da servire
        updateSending(-1)

        return


class poolWorker(threading.Thread):
    def __init__(self, completedLock, completedMask, sTracker, socketLock, md5, id, fileName, sid):
        threading.Thread.__init__(self)
        self.fileName = fileName
        self.id = id
        self.stopped = False
        self.working = False
        self.completedLock = completedLock
        self.completedMask = completedMask
        self.sTracker = sTracker
        self.socketLock = socketLock
        self.md5 = md5
        self.part_id = None
        self.peer = []
        self.sid = sid

    def assign(self, part_id, peer_details):
        self.part_id = part_id
        self.peer = peer_details
        self.working = True

    def run(self):
        while (self.stopped is False):
            if (self.working == True):  # se ho del lavoro da svolgere
                while True:
                    sockDownload = randomConnection(self.peer[0], int(self.peer[1]))
                    if sockDownload is None:
                        print("[POOL_WORKER_" + str(self.id) + "] ERROR: Cannot connect to the peer", self.peer[0], ":",
                              self.peer[1], ". Retry...")
                        getch()
                    else:
                        break

                message = "RETP" + str(self.md5) + str(self.part_id).zfill(8)

                print("[POOL_WORKER" + str(self.id) + "] <" + str(message))

                sockDownload.sendall(message.encode('utf-8'))

                data = recvExact(sockDownload, 10).decode('utf-8')  # punto a ricevere "AREP#chunk"
                n_chunks = int(data[4:])

                if debug is True:   print("[POOL_WORKER" + str(self.id) + "] #chunk = " + str(n_chunks))

                partName = self.md5 + '.' + str(self.part_id).zfill(8)
                partFile = open(os.path.join(script_dir, partName), "wb")

                for index in range(0, n_chunks):
                    data = recvExact(sockDownload, 5)  # ricevo "Lenchunk_i[5Bytes]"
                    size = int(data.decode('utf-8'))

                    data = recvExact(sockDownload, size)  # ora ricevo ESATTAMENTE il contenuto binario del chunk

                    partFile.write(data)  # scrivo il chunk nel file di destinazione

                partFile.close()
                sockDownload.shutdown(socket.SHUT_RDWR)
                sockDownload.close()

                message = ("RPAD" + str(self.sid) + str(self.md5) + str(self.part_id).zfill(8))
                self.socketLock.acquire()

                self.sTracker.sendall(message.encode('utf-8'))
                print("[POOL_WORKER" + str(self.id) + "] <" + str(message))
                message = recvExact(self.sTracker, 12).decode('utf-8')  # ricevo "APAD"#Part[8B]
                self.socketLock.release()
                print("[POOL_WORKER" + str(self.id) + "] >" + str(message))

                self.completedLock.acquire()
                setCompleted(self.md5, self.part_id)
                self.completedLock.release()

                self.working = False
            return

    def isBusy(self):
        return self.working

    def stop(self):
        self.stopped = True


class proxyThread(threading.Thread):
    def __init__(self, p2pPort):
        threading.Thread.__init__(self)
        self.p2pPort = p2pPort
        self.enabled = False
        self.sockP2p = None

    def run(self):
        if (self.sockP2p is None):

            self.sockP2p = v4v6.create_server_sock(("", int(self.p2pPort)))

            # se il dispositivo su cui sto eseguendo la directory non supporta il "dual_stack" allora si crea una socket
            # multipla per coprire sia v4 che v6
            if not v4v6.has_dual_stack(self.sockP2p):
                self.sockP2p.close()
                self.sockP2p = v4v6.MultipleSocketsListener([("0.0.0.0", int(self.p2pPort)), ("::", int(self.p2pPort))])
            while True:
                clientsock, clientAddress = self.sockP2p.accept()
                if (debug is True): print("[PEER_PROXY] Received connection from: " + str(clientAddress))

                if (self.enabled is True):
                    try:
                        newthread = peerWorker(clientAddress, clientsock)
                        newthread.start()
                    except:
                        print("[PEER_PROXY] ERROR: Cannot create a new peerWorker.")
                else:
                    if (debug is True):  print("[PEER_PROXY] WARNING: Connection refused due i'm DISABLED.")
                    clientsock.shutdown(socket.SHUT_RDWR)
                    clientsock.close()

    def enable(self):
        if (debug is True):  print("[PEER_PROXY] INFO: Proxy ENABLED.")
        self.enabled = True

    def disable(self):
        if (debug is True):  print("[PEER_PROXY] INFO: Proxy DISABLED.")
        self.enabled = False


############################################ FUNZIONI #############################################
# Funzione che consente di avere una ricezione di esattamente n_bytes
def recvUntil(miaSocket, pattern):
    letto = b""
    while True:
        temp = b""
        temp = recvExact(miaSocket, len(pattern))

        if (temp == pattern.encode('utf-8')):  # se ho letto il terminatore
            break  # ho finito di leggere
        else:
            letto += temp
    return letto


def list2string(lista):
    stringa = ""
    try:
        for el in lista:
            stringa += str(el)
    except:
        print("LIST2STRING EXCEPTION. ABORT!")
        return ""
    return stringa


def addFile(sock, Session_ID, sLock, sharedDict, file_name, file_description, config):
    while True:
        # script_dir = os.path.dirname(__file__)  # questo è il path dove si trova questo script
        # rel_path = str(input("Insert the file name (extension included): "))
        # file_name = os.path.join(script_dir, rel_path)
        try:
            mioFile = open(file_name, "rb")
            break
        except:
            print("FileNotFound:", file_name)
            return "FNF"  # FileNotFound

    fileData = mioFile.read()  # carico tutto il contenuto del file nella variabile "data"
    mioFile.close()

    fileMd5 = hashlib.md5(fileData + config["peer_ips"].encode('utf-8')).hexdigest()

    if fileMd5 in sharedDict:
        return "FAS"  # FileAlreadyShared
    else:
        data = str(fileMd5)

    # fileDescription = str(input("Insert the file description (max 100chars): "))

    if len(file_description) < 100:  # se "fileDescription" è più corta di 100 caratteri
        fileDescription = file_description.ljust(100)  # concateno gli spazi necessari alla descrizione originale
    else:  # se "fileDescription" ha almeno 100 caratteri
        fileDescription = file_description[0:100]  # prendo i primi 100 caratteri

    size = len(fileData)
    if size > 9999999999:
        return "FTB"  # Filesize must fit into 10B, so this file it's too big. Abort.")

    # parts_min = (size // 999999) + 1 # la dimensione di ciascuna parte dev'essere contenibile in 6B

    # n_parts = random.randrange(parts_min, min(9999999,size) ,1) # genero casualmente il numero di parti per il file

    # controllo che "il residuo" ossia la dimensione dell'ultima parte non superi la dimensione delle altri parti
    # (se succede semplicemente incremento il numero di parti)
    # part_size = size // n_parts
    # last_size = size - (n_parts * part_size)

    # if(last_size > part_size):  n_parts += last_size // part_size
    # else:                       n_parts += 1

    # VERSIONE2 (QUELLA CORRETTA)
    # while True:
    #    lenPart = random.randint(1, min(size,999999))
    #    nParts = size // lenPart
    #    residuo = size - (lenPart * nParts)
    #
    #    while(residuo > 0):
    #        residuo = residuo - lenPart
    #        nParts = nParts + 1
    #
    #    if(nParts <= 99999999):
    #        break

    # VERSIONE3 (al minimo di N tentativi)
    n = 2

    lpt = []
    npt = []
    for i in range(0, n):
        lpt.append(0)
        npt.append(0)

    i = 0
    while (i < n):
        while True:
            lpt[i] = random.randint(1, min(size, 999999))
            npt[i] = size // lpt[i]
            residuo = size - (lpt[i] * npt[i])

            while (residuo > 0):
                residuo = residuo - lpt[i]
                npt[i] = npt[i] + 1

            if (npt[i] <= 99999999):
                break
        i += 1
    nParts = min(npt)
    lenPart = lpt[npt.index(nParts)]

    # msg = "ADDR" + Session_ID + str(size).zfill(10) + str(part_size).zfill(6) + fileDescription + str(fileMd5)
    msg = "ADDR" + Session_ID + str(size).zfill(10) + str(lenPart).zfill(6) + fileDescription + str(fileMd5)

    sLock.acquire()

    print("[PEER] <", msg)
    sock.sendall(msg.encode('utf-8'))
    data = recvExact(sock, 12).decode('utf-8')
    print("[PEER] >", data)

    sLock.release()

    if (data[0:4] != "AADR"):
        print("[PEER] ERROR: I was expecting an AADR but i received", data[0:4], ". Abort.")
        return "ERR"

    try:
        returned_parts = int(data[4:])
    except:
        print("[PEER] ERROR: Tracker returned a not-integer value for #part. Abort.")
        return "ERR"

    # if(returned_parts != n_parts):  print("[PEER] WARNING: Tracker returned #part=" + str(returned_parts) + " but i was expecting n_parts=" + str(n_parts) + ". Please check.")
    if (returned_parts != nParts):  print(
        "[PEER] WARNING: Tracker returned #part=" + str(returned_parts) + " but i was expecting nParts=" + str(
            nParts) + ". Please check.")

    mask = []
    for i in range(0, returned_parts):  mask.append('1')

    lockSharedDict.acquire()
    # sharedDict[fileMd5] = (file_name, part_size, returned_parts, mask)
    sharedDict[fileMd5] = (file_name, lenPart, returned_parts, mask)
    lockSharedDict.release()

    return str(fileMd5) + ',' + str(returned_parts)


def checkStatus(sid, md5, n_parts, sock, sLock):
    msg = "FCHU" + sid + md5
    sLock.acquire()
    sock.sendall(msg.encode('utf-8'))

    data = recvExact(sock, 4).decode('utf-8')
    if (data != "AFCH"):
        print("[PEER] I was expecting an AFCH from tracker but i received an " + str(data) + ". Abort.")
        sLock.release()
        return None

    try:
        hitpeer = int(recvExact(sock, 3).decode('utf-8'))
    except:
        print("[PEER] ERROR: I received a not-integer value (" + str(data) + ")for #hitpeer. Please check. Abort.")
        sLock.release()
        return None

    toRead = 55 + 5  # IpP2P[55B].PortP2P[5B]
    if ((n_parts % 8) == 0):
        bytesMaschera = int(n_parts) // 8
    else:
        bytesMaschera = (int(n_parts) // 8) + 1

    peerList = []

    for i in range(0, hitpeer):
        data = recvExact(sock, toRead).decode('utf-8')  # IpP2P[55B].PortP2P[5B]#
        temp = recvExact(sock, bytesMaschera)  # maschera in bytes
        maschera = bitstring.BitArray(temp)  # maschera in sequenza di bit

        # Dalla maschera tolgo gli eventuali zeri finali aggiunti dal tracker per raggiungere il multiplo di 8 necessario a contenere n_parts
        mask = []
        for i in range(0, n_parts):
            # mask.append(maschera[i]) # inserisco, carattere per carettere, i primi "n_parts" bit della maschera
            if maschera[i] is True:
                mask.append('1')
            else:
                mask.append('0')

        peerList.append((data[0:55], data[55:60], mask))

    sLock.release()
    return peerList


def clear():
    if os.name == 'nt':  # Windows
        os.system('cls')
    else:  # Mac e Linux
        os.system('clear')


def downloadFile(result, Session_ID, sTracker, sLock):
    md5 = result[0]
    file_name = result[1].strip()
    file_size = int(result[2])
    part_size = int(result[3])
    n_parts = file_size // part_size

    file_path = os.path.join(script_dir, file_name)

    if n_parts * part_size < file_size:    n_parts += 1

    # if(md5 in sharedDict):
    # while True:
    #    scelta = input("[PEER] WARNING: You already own this file. Do you want to overwrite it? [y/n]")
    #    if(scelta == 'n'):
    #        return
    #    elif(scelta == 'y'):
    #        break
    #    else:
    #        print("Wrong input. Only 'y' or 'n'. Retry...")

    completedLock = threading.Lock()
    completedMask = []
    assignedMask = []  # maschera in cui, ogni volta che assegno ad un worker una parte me la segno

    for i in range(0, n_parts):
        completedMask.append('0')
        assignedMask.append('0')

    lockSharedDict.acquire()
    sharedDict[md5] = (file_name, part_size, n_parts, completedMask)
    lockSharedDict.release()

    lista = []
    for i in range(0, n_parts): lista.append(-1)
    inUseDict[md5] = lista

    partsLock = threading.Lock()

    updater = partsUpdater(md5, Session_ID, n_parts, sTracker, partsLock, sLock)
    updater.start()

    # Creo ed avvio il pool di downloader
    # try:
    # while True:
    # pool_size = int(input("[PEER] Insert the pool size:"))
    # if(pool_size > n_parts):    print("[PEER] Pool size must be <= " + str(n_parts))
    # else:                       break
    # except:
    #    if(debug is True):  print("[PEER] WARNING: Not-integer inserted. I'll use the default value (5).")
    #    pool_size = 5

    pool_size = min(10, n_parts)

    poolList = []
    for i in range(0, pool_size):
        poolList.append(poolWorker(completedLock, completedMask, sTracker, sLock, md5, i, file_name, Session_ID))
        poolList[i].start()
    # if(debug is True):  print("INFO: Pool correctly started.")

    while True:
        if (len(
                partsList) == n_parts):  # posso procedere solo dopo che l'updater ha processato almeno una volta la partsList
            partsLock.acquire()
            try:
                # Devo processare partsList al fine di mettere in toChoose tutti gli ID delle parti più rare tra quelle che mi mancano
                toChoose = []  # lista in cui metto l'id delle parti tra cui scegliere la prossima da scaricare
                index = 0  # indice per scorrere la lista
                value = int(partsList[-1][1])  # prendo la disponibilità massima tra le parti
                stop = False  # (part_id, *disponibilità* , [(peerA,portA),(peerB,portB),...])

                while (stop is False) and (index < len(partsList)):
                    if int(partsList[index][1]) <= value:
                        if assignedMask[int(partsList[index][0])] == '0':
                            value = int(partsList[index][1])
                            toChoose.append(int(partsList[index][0]))
                        index += 1
                    else:
                        stop = True

                # print("TO_CHOOSE:", toChoose)     #DEBUG
                # print("ASSIGNED_MASK:", list2string(assignedMask)) #DEBUG

                # Scelgo la parte
                part_id = random.choice(toChoose)
                if debug is True:  print(
                    "[PEER] Random choosed part " + str(part_id) + " available from " + str(value) + " peers.")

                # Recupero la lista di peer
                trovato = False
                peers = []
                indice = 0
                while (trovato is False) and (indice < len(partsList)):
                    if partsList[indice][0] == part_id:
                        peers = partsList[indice][2]
                        trovato = True
                    else:
                        indice += 1

                peer_index = random.randrange(0, len(peers))
                peer_details = peers[peer_index]

                if debug is True:  print("[PEER] Random choosed to require the part " + str(part_id) + " to the peer",
                                         peer_details)

            finally:
                partsLock.release()

            index = 0
            while True:
                if poolList[index].isBusy() is False:
                    poolList[index].assign(part_id, peer_details)
                    if debug is True: print("[PEER] Part " + str(part_id) + " assigned to PoolWorker " + str(index))
                    break
                else:
                    index += 1

                if index == pool_size:    index = 0  # gestione del pool "a buffer circolare"

            assignedMask[part_id] = '1'

            # if(part_id < len(assignedMask)):
            #    assignedMask = assignedMask[:part_id] + '1' + assignedMask[(part_id+1):]
            # else:   # se ho assegnato l'ultima parte (in ordine di ID).
            #    assignedMask = assignedMask[:part_id] + '1'

            print("[PEER] Download progress: parts required", assignedMask.count('1'), "of", n_parts)

            if '0' not in assignedMask:
                break
            # if(assignedMask == ('1' * n_parts)): break  # se ho assegnato tutte le parti posso uscire da questo ciclo

    updater.stop()  # fermo l'updater

    for pool in poolList:  # per ogni processo del Pool
        pool.stop()  # fermo il PoolWorker
        pool.join()  # attendo l'effettiva terminazione del thread

    print("[PEER] All parts successfully retrived. Start file's assembling.")

    dataFile = open(file_path, "wb")
    for i in range(0, n_parts):
        partName = str(md5) + '.' + str(i).zfill(8)
        partFile = open(os.path.join(script_dir, partName), "rb")
        dataFile.write(partFile.read())
        partFile.close()
        while True:
            if partLocked(md5, i) is False:
                break
        os.remove(os.path.join(script_dir, partName))
    dataFile.close()

    print("[PEER] Download successfully completed!")
    stato = "OK"
    return stato


def explodeIpv4(address):
    ip_temp = address.split('.')
    v4_exp = ""

    for index in range(0, 4):
        v4_exp += str(ip_temp[index]).zfill(3)
        if index < 3:
            v4_exp += '.'

    return v4_exp


def explodeIpv6(address):
    return str(ipaddress.IPv6Address(address).exploded)


def getch():
    input("Press any key to continue...")
    return


def implodeIpv4(address):
    ip_temp = address.split('.')
    out = ""

    for index in range(0, 4):
        out += str(int(ip_temp[index]))
        if index < 3:
            out += '.'

    return out


def implodeIpv6(address):
    return str(ipaddress.IPv6Address(address).compressed)


def getSending():
    global sending
    return sending


def updateSending(inc):
    global sending
    lockSending.acquire()
    sending += int(inc)
    lockSending.release()
    return


def loadConfiguration():
    rel_path = "peerConfiguration.csv"
    config_file = os.path.join(script_dir, rel_path)

    try:
        mioFile = open(config_file, "rt")
    except:
        print("WARNING: Configuration's file not found.")
        return None
    from_csv = mioFile.read()
    mioFile.close()

    from_csv = from_csv.split(',')
    config = {}
    if len(from_csv) != 8:
        print(
            "ERROR: Wrong number of parameters inside the configuration file (" + str(len(from_csv)) + "instead of 8).")
        return None
    else:
        config["peer_ipv4"] = implodeIpv4(from_csv[0])
        config["peer_ipv6"] = implodeIpv6(from_csv[1])
        config["peer_port"] = str(from_csv[2]).zfill(5)
        config["peer_ips"] = from_csv[3]
        # config["peer_ips"] = explodeIpv4(config["peer_ipv4"]) + '|' + explodeIpv6(config["peer_ipv6"])

        config["tracker_ipv4"] = implodeIpv4(from_csv[4])
        config["tracker_ipv6"] = implodeIpv6(from_csv[5])
        config["tracker_port"] = str(from_csv[6]).zfill(5)
        config["tracker_ips"] = from_csv[7]
        # config["tracker_ips"] = explodeIpv4(config["tracker_ipv4"]) + '|' + explodeIpv6(config["tracker_ipv6"])

    if debug is True:
        print("[INFO] From configuration's file i rode:")
        for key, value in config.items():
            print(str(key) + "\t:\t" + str(value))

        getch()
        clear()
    return config


def login(sock, sLock, config):
    msg = "LOGI" + config["peer_ips"] + str(config["peer_port"]).zfill(5)
    print("[PEER] <" + msg)

    sLock.acquire()

    sock.sendall(msg.encode('utf-8'))
    data = recvExact(sock, 20).decode('utf-8')

    sLock.release()

    print("[PEER] >" + data)

    if data[0:4] != "ALGI":
        print("[PEER] WARNING: received command " + data[0:4] + " when expecting ALGI.")

    if data[4:] == "0000000000000000":
        if debug is True:  print("[PEER] Warning: received a all-zeroes SID.")
    else:
        print("[PEER] INFO: Login performed successfully!")

    return data[4:]


def logout(sock, Session_ID, sLock, peerProxy):
    msg = "LOGO" + Session_ID
    print("[PEER] <" + msg)

    sLock.acquire()

    sock.sendall(msg.encode('utf-8'))
    data = recvExact(sock, 14).decode('utf-8')

    sLock.release()

    print("[PEER] >" + data)

    if data[0:4] == "NLOG":
        print("[PEER] Cannot perform the logout because tracker replied with an NLOG.")
        if debug is True:  print("[PEER] #partdown = " + data[4:])
        return False

    if data[0:4] == "ALOG":
        if debug is True:
            print("[PEER] Tracker's socket closed successfully.")
            print("[PEER] #partdown = " + data[4:])
        print("[PEER] Waiting 60 seconds.")
        time.sleep(60)
        peerProxy.disable()

        last_value = -1
        while getSending() > 0:
            if (
                    last_value != getSending()):  # in questo modo stampo la riga seguente solo quando il numero di invii cambia
                last_value = getSending()  # altrimenti farei inutilmente flooding nel terminale
                print("[PEER] " + str(last_value) + " sending left before perform the logout. Please wait...")

        try:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except:
            print("[PEER] WARNING: Error when trying to close peer2tracker socket.")
            print("[PEER] Logout performed with some warning.")
            return True

        print("[PEER] All sendings completed. Now you are logged out.")
        return True

    print("[PEER] Warning: received " + data[0:4] + " when expecting an NLOG or ALOG. Please check the tracker. Abort.")
    return False


def ordinamento(elemento):
    return elemento[1]


def partAcquire(md5, part_id):
    return partModify(md5, part_id, 1)


def partModify(md5, partId, inc):
    part_id = int(partId)
    if partUpdate(md5) is False:
        return False

    lockUseDict.acquire()
    locked = inUseDict[md5]  # MD5 = (-1,-1,-1,0,0,0,1,40,0,-1,0, ...) dove la lunghezza è n_parts

    if part_id not in range(0, len(locked)):
        print("ERROR: partModify(" + str(md5) + ',' + str(part_id) + ',' + str(inc) + ") but there are only " + str(
            len(locked)) + " parts.")
        lockUseDict.release()
        return False

    if locked[part_id] == -1:
        print("ERROR: partModify(" + str(md5) + ',' + str(part_id) + ',' + str(
            inc) + ") but i don't have this part (-1).")
        lockUseDict.release()
        return False

    if (inc != 1) and (inc != -1):
        print("ERROR: partModify(" + str(md5) + ',' + str(part_id) + ',' + str(
            inc) + ") but the inc_value must be '1' or '-1'.")
        lockUseDict.release()
        return False

    if (locked[part_id] == 0) and (int(inc) == 0):
        print("ERROR: partModify trying to release the part=" + str(part_id) + " but it's not locked.")
        lockUseDict.release()
        return False

    locked[part_id] += int(inc)
    inUseDict[md5] = locked

    lockUseDict.release()
    return True


def partRelease(md5, part_id):
    return partModify(md5, part_id, -1)


def partUpdate(md5):
    lockUseDict.acquire()
    locked = inUseDict[md5]  # MD5 = (-1,-1,-1,0,0,0,1,40,0,-1,0, ...) dove la lunghezza è n_parts
    shared = sharedDict[md5][3]  # MD5 = (file_name, n_parts, len_parts, mask)

    if (len(locked) != len(shared)):
        print("ERROR: partUpdate(" + str(md5) + ") but len(locked)=" + str(
            len(locked)) + " NOT EQUAL TO len(shared)=" + str(len(shared)) + ". Abort.")
        lockUseDict.release()
        return False

    for index in range(0, len(locked)):
        # se inUseDict non sapeva che la part_id=index era stata scaricata dal peer, allora aggiorno dicendo che è disponibile.
        if ((locked[index] == -1) and (shared[index] == 1)):    locked[index] = 0

    inUseDict[md5] = locked
    lockUseDict.release()


def partLocked(md5, part_id):
    lockUseDict.acquire()
    if (md5 not in inUseDict):
        print("ERROR: partLocked(" + str(md5) + ',' + str(part_id) + ") but that MD5 isn't inside inUseDict.")
        lockUseDict.release()
        return -1

    locked = inUseDict[md5]  # MD5 = (-1,-1,-1,0,0,0,1,40,0,-1,0, ...) dove la lunghezza è n_parts

    lockUseDict.release()

    if (part_id not in range(0, len(locked))):
        print("ERROR: partLocked(" + str(md5) + ',' + str(part_id) + ") but there are only" + str(
            len(locked)) + " parts.")
        return -1

    if (locked[part_id] == 0):
        return False
    else:
        return True


def searchFile(sock, Session_ID, sLock, research):
    # if len(research) < 20:  # se "research" è più corta di 20 caratteri
    #    to_be_added = " " * (20 - len(research)) # creo una stringa con gli spazi necessari per giungere a 20 caratteri
    #    research = research + to_be_added  # concateno gli spazi necessari alla chiave di ricerca inserita
    # if len(research) > 20:  # se "fileDescription" ha più di 20 caratteri
    #    research = research[0:20]  # prendo i primi 20 caratteri

    msg = "LOOK" + Session_ID + research

    sLock.acquire()
    print("[PEER] <" + msg)
    sock.sendall(msg.encode('utf-8'))

    # "ALOO".#idm5[3B].{File_md5_i[32B].File_name_i[100B].len_file[10B].len_part[6B]}
    data = recvExact(sock, 7).decode('utf-8')  # ricevo "ALOO.#idm5"
    if data[0:4] != "ALOO":
        print("[PEER] ERROR: Received " + str(data[0:4]) + " when expecting an ALOO. Abort.")
        sLock.release()
        return

    try:
        idm5 = int(data[4:])
    except:
        print("[PEER] ERROR: Received a non-integer #idm5 from tracker. Abort.")
        sLock.release()
        return

    if idm5 == 0:
        print("[PEER] >", data)
        print("[PEER] Tracker returned zero items. Search completed.")
        sLock.release()
        return

    print("[PEER] Found " + str(idm5) + " results.")
    resultList = []

    for i in range(0, idm5):
        data = recvExact(sock, 148).decode(
            'utf-8')  # ricevo {File_md5_i[32B].File_name_i[100B].len_file[10B].len_part[6B]}

        file_md5 = str(data[0:32])
        file_name = str(data[32:132])
        len_file = int(data[132:142])
        len_part = int(data[142:])

        resultList.append((file_md5, file_name, len_file, len_part))

    sLock.release()

    return resultList

    # while True:
    #    choice = str(input("\nDo you want to download one of this files? [y/n]:"))
    #    if choice == "n":
    #        return  # torno al menu principale in quanto non ho altro da fare quì
    #    if choice == "y":
    #        break  # procedo con il download

    # while True:
    #    try:
    #        print("\nInsert the index of the file that you want to download [0-" + str(idm5 - 1) + "]: ")
    #        index_file = int(input())
    #    except:
    #        print("Please insert an integer value. Retry...")
    #        continue

    #    if index_file in range(0, idm5):
    #        break
    #    else:
    #        print("\nThe choice must be in range[0," + str(idm5 - 1) + "]. Retry...")

    # downloadFile(resultList[index_file], Session_ID, sock, sLock)


def randomConnection(HOST, PORT):
    ips = HOST.split("|")  # in questo modo ips[0] conterrà ipv4_directory, ips[1] conterrà ipv6_directory
    coin = random.randint(0, 1)

    if coin == 0:  # connessione con ipv4
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        v4 = str(implodeIpv4(ips[0]))
        try:
            sock.connect((v4, int(PORT)))
            if (debug is True):  print("INFO: Connected using ipv4.")
        except:
            print("ERROR: randomConnection unable to connect using ipv4.")
            return None

    else:  # connessione con ipv6
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)

        v6 = str(implodeIpv6(ips[1]))
        try:
            sock.connect((v6, int(PORT), 0, 0))
            if (debug is True):  print("INFO: Connected using ipv6.")
        except:
            print("ERROR: randomConnection unable to connect using ipv6.")
            return None
    return sock


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


def saveConfiguration(actualConfig):
    rel_path = "peerConfiguration.csv"
    file_name = os.path.join(script_dir, rel_path)

    data_csv = ""
    for value in actualConfig.values():
        data_csv += str(value) + ','

    data_csv = data_csv[:-1]

    try:
        mioFile = open(file_name, "wt")
    except:
        print("INFO: Problemi nella scrittura del file di configurazione!")
        return None

    mioFile.write(data_csv)
    mioFile.close()
    return True


def setCompleted(md5, part_id):  # restituisce False se qualcosa è andato storto, True se ha completato con successo
    if (len(md5) != 32):
        print("WARNING: setCompleted called with a wrong lenght's MD5. Abort.")
        return False

    try:
        int(part_id)
    except:
        print("ERROR: setCompleted called with a non-integer part_id. Abort.")
        return False

    if (md5 not in sharedDict):
        print("ERROR: setCompleted called with MD5=" + str(md5) + " but there is no match inside sharedDict. Abort.")
        return False

    lockSharedDict.acquire()
    tupla = sharedDict[md5]  # MD5 = (file_name, n_parts, len_parts, mask)
    maschera = tupla[3].copy()

    if (len(maschera) < part_id):
        print("ERROR: setCompleted called with part_id=" + str(part_id) + " but len(mask)=" + str(
            len(maschera)) + ". Abort.")
        lockSharedDict.release()
        return False

    if (maschera[part_id] == '1'):
        print("WARNING: setCompleted called with part_id=" + str(
            part_id) + " but it's already '1' inside the mask. Abort.")
        lockSharedDict.release()
        return False

    # print("Maschera pre:  ", list2string(maschera))#DEBUG
    maschera[part_id] = '1'
    # print("Maschera post: ", list2string(maschera))#DEBUG

    # if(part_id < len(mask)):
    #    mask = mask[:(part_id)] + '1' + mask[(part_id+1):]
    # else:
    #    mask = mask[:(part_id)] + '1'

    # print("----- SHAREDDICT_MASK PRIMA DI AGGIORNAMENTO -----")     #DEBUG
    # print(list2string(sharedDict[md5][3]))                          #DEBUG
    sharedDict.update({md5: (tupla[0], tupla[1], tupla[2], maschera)})
    # print("----- SHAREDDICT_MASK DOPO L'AGGIORNAMENTO -----")       #DEBUG
    # print(list2string(sharedDict[md5][3]))                          #DEBUG
    lockSharedDict.release()

    lockUseDict.acquire()
    if (md5 in inUseDict):
        lista = inUseDict[md5]
        if (lista[part_id] == -1):
            lista[part_id] = 0
            inUseDict[md5] = lista
        else:
            print("WARNING: setCompleted expected a '-1' value inside inUseDict, but ", lista[part_id], " found!")
    lockUseDict.release()

    return True


# Istanzio il peerProxy
def istanziaPeerProxy(config):
    while True:
        try:
            peerProxy = proxyThread(config["peer_port"])
            peerProxy.start()
            break
        except:
            print("ERROR: Exception when creating a peer_proxy thread to serve. I'll retry...")
            getch()

    return peerProxy


#############################################  MAIN  #############################################
# Istanzio il thread che risponde all'interfaccia web
while True:
    while True:
        try:
            talker = webTalker()
            talker.start()
            break
        except:
            print("ERROR: Exception when creating a webTalker thread to serve. I'll retry...")
            getch()
    break

# Lancio il menu principale
esci = False

while (esci == False):
    # getch()
    # clear()

    # print(' '*27 + " ________                       _   ")
    # print(' '*27 + "/__   __/_  _ __ _ __ ___ _ __ | |_ ")
    # print(' '*27 + "  /  // _ \| '__| '__/ _ \ '_ \| __|")
    # print(' '*27 + " /  /| |_| | |  | | |  __/ | | | |_ ")
    # print(' '*27 + "/__/  \___/|_|  |_|  \___|_| |_|\__|")
    # print()
    # print("    PEER    [", config["peer_ipv4"],    '|', config["peer_ipv6"],    ':', config["peer_port"],   "]")
    # print("    TRACKER [", config["tracker_ipv4"], '|', config["tracker_ipv6"], ':', config["tracker_port"],"]")

    # if(logged is True):
    #    print("    SID: ",sid)
    #    print("    Shared files:")
    #    for md5, tupla in sharedDict.items():
    #        presenti = tupla[3].count('1')

    #        print("     Md5=" + str(md5) + " Len_parts=" + str(tupla[1]).ljust(6,' ') + " Owned_parts=" + str(presenti) + " of " + str(tupla[2]))

    # print('_' * 90)
    # print(" 1 - Login")
    # if(logged is True):
    #    print(" 2 - Add file")
    #    print(" 3 - Search files")
    #    print(" 4 - Logout")

    # print("\n 0 - Exit")

    # try:
    #    if(logged is True):
    #        scelta = int(input("Action to perform [0-4]: "))
    #    else:
    #        scelta = int(input("Action to perform [0-1]"))
    # except:
    #    print("Please insert only numbers. Retry...")
    #    continue

    # Exit
    # if(scelta == 0):
    #    esci = True
    #    continue

    # Login
    # elif(scelta == 1):
    #    if(sTracker == None):
    # tracker_ips = str(explodeIpv4(config["tracker_ipv4"])) + '|' + str(explodeIpv6(config["tracker_ipv6"]))
    #        tracker_ips = str(config["tracker_ipv4"]) + '|' + str(config["tracker_ipv6"])
    #        sTracker = randomConnection(tracker_ips, int(config["tracker_port"]))

    #    if(sTracker != None):
    #        sid = login(sTracker, lockSocket)
    #        if(sid != "0000000000000000"):
    #            logged = True
    #            peerProxy.enable()
    #    else:
    #        print("[PEER] Cannot create a connection with the tracker. Please check parameters.")

    #    continue

    # Add_file
    # elif((scelta == 2)and(logged is True)):
    #    addFile(sTracker, sid, lockSocket, sharedDict)
    #    continue

    # Search_files
    # elif((scelta == 3)and(logged is True)):
    #    while True:
    #        research = input("Insert the keyword to search: ")
    #        if(research != ""): break
    #    searchFile(sTracker, sid, lockSocket, research)
    #    continue

    # Logout
    # elif((scelta == 4)and(logged is True)):
    #    esito = logout(sTracker, sid, lockSocket, peerProxy)
    #    if(esito is True):  # Logout concesso dal tracker
    #        logged = False
    #        sTracker = None
    #        sid = ""
    #        lockSharedDict.acquire()
    #        sharedDict.clear()
    #        lockSharedDict.release()
    #    continue

    # else:
    #    print("Wrong selection. Retry...")
    #    continue

    # print("See you soon!")
    continue
