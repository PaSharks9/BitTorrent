#!/usr/bin/env python3

# ########################################### LIBRERIE ############################################
import hashlib
import ipaddress
import os
import random
import socket
import sys
import threading
import time
import v4v6

# ########################################### Utilities ############################################
script_dir = os.path.dirname(__file__)  # E' il path dove si trova questo script
debug = False
lockSending = threading.Lock()
lockSocket = threading.Lock()
lockSharedDict = threading.Lock()


def logout(sock, Session_ID, sLock, peerProxy):
    msg = "LOGO" + Session_ID
    print("[PEER] <" + msg)

    sLock.acquire()

    sock.sendall(msg.encode('utf-8'))
    data = recvExact(sock, 14).decode('utf-8')

    sLock.release()

    print("[PEER] >" + data)

    if (data[0:4] == "NLOG"):
        print("[PEER] Cannot perform the logout because tracker replied with an NLOG.")
        if (debug is True):  print("[PEER] #partdown = " + data[4:])
        return False

    if (data[0:4] == "ALOG"):
        if (debug is True):
            print("[PEER] Tracker's socket closed successfully.")
            print("[PEER] #partdown = " + data[4:])
        print("[PEER] Waiting 60 seconds.")
        time.sleep(60)
        peerProxy.disable()

        last_value = -1
        while (getSending() > 0):
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


def clear():
    if os.name == 'nt':  # Windows
        os.system('cls')
    else:  # Mac e Linux
        os.system('clear')


def getch():
    input("Press any key to continue...")
    return


def getSending():
    global sending
    return sending


def updateSending(inc):
    global sending
    lockSending.acquire()
    sending += int(inc)
    lockSending.release()
    return


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


def recvUntil(miaSocket, pattern):
    letto = b""
    while True:
        temp = b""
        temp = recvExact(miaSocket, len(pattern))

        if temp == pattern.encode('utf-8'):  # se ho letto il terminatore
            break  # ho finito di leggere
        else:
            letto += temp
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


class webTalker(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.killed = False
        self.webHost = '127.0.0.1'  # Accetto solo connessioni da localhost (modificandolo è possibile agganciarsi ad
        # una macchina distinta
        self.webPort = 3001  # La porta sarà incrementata fino a trovare la prima libera
        self.webSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.webConnection = None
        self.webAddress = None
        print("INFO: Please connect the WebInterface to the port ", self.webPort)
        self.webAddress = None
        self.sTracker = None
        self.config = {}
        self.peerProxy = None
        self.logged = False

        # Trovo una porta libera
        while self.webPort < 65636:
            try:
                self.webSocket.bind((self.webHost, self.webPort))
                break
            except:
                self.webPort = self.webPort + 1

        self.webSocket.listen(1)  # Mi pongo in ascolto
        print("INFO: Please connect the WebInterface to the port ", self.webPort)
        self.webConnection, self.webAddress = self.webSocket.accept()  # Aspetto che l'interfaccia web si connetta
        self.webSocket.close()
        self.sid = ""

    def run(self):
        while self.killed is False:
            data = recvExact(self.webConnection, 4)
            data = data.decode('utf-8')
            print("[MONKEY-PEER] Ricevuto dal web comando: ", data)

            if data == "GETP":
                print("[MONKEY-PEER] -GETP recv-")
                # Parametri non trovati sul file di log
                dataNF = ""
                # Parametri trovati
                data = "127.0.0.1,::1,5000,127.0.0.1,::1,3000"

            elif data == "SETP":
                data = recvUntil(self.webConnection, '%').decode('utf-8')
                lista = data.split(',')
                print("[MONKEY-PEER] -SETP recv-")
                print("[MONKEY-PEER] Parametri ricevuti: ")
                for param in lista:
                    print("- " + str(param))

                data = "SAVD"

            # Ricevuto dalla funzione logged() di webUI, chiede se siamo loggati
            # Fino a quando non arriva un LOGI il sid è sloggato, una volta fatto il logi si da un sid da loggato
            elif data == "LOG?":
                if self.logged is True:
                    data = self.sid
                else:
                    data = "False"

            elif data == "HOME":
                data = "abcdefghiasmckaldkfideldlsopie32|100|5|10"

<<<<<<< HEAD
=======
            elif data == "FIND":
                print("[MONKEY-PEER] RICEVUTO DAL WEB:" + data)
                monkeyDict = {'helmet': ('e11f7b6e50eb65e311a591a244210c69', 'helmet', 100, 10),
                              'mandarino': ('mandarinoeb65r311a591a2f421ac64', 'mandarino', 1000, 100),
                              'cane': ('012345678912345678912', 'sally', 40, 20)
                              }
                # Leggo la chiave da ricercare (già formattata a 20 caratteri da WebUI)
                data = recvExact(self.webConnection, 20)
                data = data.decode('utf-8')

                # File_md5_i[32B].File_name_i[100B].len_file[10B].len_part[6B]
                keyword = data.strip()
                result = []
                if keyword == "*":
                    for key in monkeyDict.keys():
                        result.append(monkeyDict[key])
                else:
                    tuplaResult = monkeyDict[keyword]
                    if tuplaResult is not None:
                        result.append(tuplaResult)

                data = ""
                if len(result) > 0:  # Se ci sono risultati converto la lista in formato CSV
                    for index in range(0, len(result)):
                        data = data + result[index][0] + ','
                        data = data + result[index][1] + ','
                        data = data + str(result[index][2]) + ','
                        data = data + str(result[index][3]) + ','

>>>>>>> develop
            elif data == "UPLD":
                data = recvUntil(self.webConnection, '%').decode('utf-8')
                lista = data.split(',')
                # data = addFile(self.sTracker, sid, lockSocket, sharedDict, lista[0], lista[1], self.config)

            elif data == "LOGI":
                self.sid = "0123456789123456"
                if self.sid != "0000000000000000" and self.sid != "":
                    self.logged = True
                    data = str(self.sid)
                else:
                    data = "ERR"

            data = data + "%"  # Uso il simbolo % come terminatore del messaggio (dall'altra parte leggerò finché non
            # lo trovo)
            self.webConnection.sendall(data.encode('utf-8'))

        try:
            self.webConnection.close()
            self.webAddress = None
        except:
            print("WARNING: Some exception when trying to close the connection to the WebInterface.")

    def kill(self):
        self.killed = True


# ############################################  MAIN  #############################################
# Istanzio il thread che risponde all'interfaccia web
while True:
    while True:
        try:
            talker = webTalker()
            talker.start()
            print("Talker successfully started!")
            break
        except:
            print("ERROR: Exception when creating a webTalker thread to serve. I'll retry...")
            getch()
    break
