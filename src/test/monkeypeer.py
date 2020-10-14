#!/usr/bin/env python3

# ########################################### LIBRERIE ############################################

import os
import socket
import threading

# ########################################### Utilities ############################################
script_dir = os.path.dirname(__file__)  # E' il path dove si trova questo script
debug = False


def clear():
    if os.name == 'nt':  # Windows
        os.system('cls')
    else:  # Mac e Linux
        os.system('clear')


def getch():
    input("Press any key to continue...")
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


class webTalker(threading.Thread):
    def __init__(self, webConnection):
        threading.Thread.__init__(self)
        self.killed = False
        self.webConnection = webConnection
        self.logged = False
        self.sid = ""

    def run(self):
        while self.killed is False:
            try:
                data = recvExact(self.webConnection, 4)
            except socket.error as e:
                print("Error: " + str(e))
                self.killed = True

            data = data.decode('utf-8')
            print("[MONKEY-PEER] Ricevuto dal web comando: ", data)

            if data == "GETP":
                # Parametri non trovati sul file di log
                dataNF = ""
                # Parametri trovati
                data = "127.0.0.1,::1,5000,127.0.0.1,::1,3000"

            # Ricevuto dalla funzione logged() di webUI, chiede se siamo loggati
            # Fino a quando non arriva un LOGI il sid e sloggato, una volta fatto il logi si da un sid da loggato
            elif data == "LOG?":
                if self.logged is True:
                    data = self.sid
                else:
                    data = "False"

            elif data == "SETP":
                try:
                    data = recvUntil(self.webConnection, '%').decode('utf-8')
                except socket.error as e:
                    print("Error: " + str(e))
                    self.killed = True

                if self.logged is True:
                    data = self.sid
                else:
                    data = "False"

            elif data == "HOME":
                data = "abcdefghiasmckaldkfideldlsopie32|100|5|10"

            elif data == "FIND":
                monkeyDict = {'helmet': ('e11f7b6e50eb65e311a591a244210c69', 'helmet', 100, 10),
                              'mandarino': ('mandarinoeb65r311a591a2f421ac64', 'mandarino', 1000, 100),
                              'cane': ('012345678912345678912', 'sally', 40, 20)
                              }
                # Leggo la chiave da ricercare (gia formattata a 20 caratteri da WebUI)
                try:
                    data = recvExact(self.webConnection, 20)
                except socket.error as e:
                    print("Error: " + str(e))
                    self.killed = True

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
                if data[-1] == ',':
                    data = data[:-1]

            elif data == "UPLD":
                try:
                    data = recvUntil(self.webConnection, '%').decode('utf-8')
                except socket.error as e:
                    print("Error: " + str(e))
                    self.killed = True

                print("[MONKEY-PEER] Data ricevuti: " + data)
                data = "e11f7b6e50eb65e311a591a244210c69,100"

            elif data == "LOGI":

                self.sid = "0123456789123456"
                if self.sid != "0000000000000000" and self.sid != "":
                    self.logged = True
                    data = str(self.sid)
                else:
                    data = "ERR"

            elif data == "LOGO":
                if self.logged:
                    data = "OK"
                else:
                    data = "false"

            elif data == "DOWN":
                try:
                    data = recvUntil(self.webConnection, '%').decode('utf-8')
                    print("Data ricevuti: " + data)
                except socket.error as e:
                    print("Error: " + str(e))
                    self.killed = True

            data = data + "%"  # Uso il simbolo % come terminatore del messaggio (dall'altra parte leggero finche non
            # lo trovo)
            self.webConnection.sendall(data.encode('utf-8'))

        try:
            self.webConnection.close()
        except:
            print("WARNING: Some exception when trying to close the connection to the WebInterface.")

    def kill(self):
        self.killed = True


# ############################################  MAIN  #############################################
# Istanzio il thread che risponde all'interfaccia web
webHost = '127.0.0.1'  # Accetto solo connessioni da localhost (modificandolo e possibile agganciarsi ad
# una macchina distinta
webPort = 3001  # La porta sara incrementata fino a trovare la prima libera
webSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

webSocket.bind((webHost, webPort))

webSocket.listen(1)  # Mi pongo in ascolto

while True:
    print("INFO: Please connect the WebInterface to the port ", webPort)
    webConnection, webAddress = webSocket.accept()  # Aspetto che l'interfaccia web si connetta

    try:
        talker = webTalker(webConnection)
        talker.start()
        print("Talker successfully started!")
    except:
        print("ERROR: Exception when creating a webTalker thread to serve. I'll retry...")
        break

webSocket.close()
