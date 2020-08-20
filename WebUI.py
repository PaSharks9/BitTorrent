import socket
from flask import Flask, render_template

# Funzione che consente di avere una ricezione di esattamente n_bytes
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

# Funzione che consente di avere una ricezione di esattamente n_bytes
def recvUntil(miaSocket, pattern):
    letto = b""    
    while True:
        temp = b""
        temp = recvExact(miaSocket,len(pattern))
        letto += temp

        if (temp == pattern.encode('utf-8')):   # se ho letto il terminatore "�"
            break  # ho finito di leggere
    return letto

# Programma
HOST = '127.0.0.1'    # The remote host
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    PORT = int(input("Digitare il numero di porta a cui collegarsi"))
    s.connect((HOST, PORT))
except:
    print("ERROR: Wrong port number. Please check, than retry...")

app = Flask(__name__)

@app.route("/")
def homepage():
    s.sendall("HOME".encode('utf-8'))
    data = recvUntil(s,"*").decode('utf-8')
    return data

@app.route("/search", methods=['GET'])  # viene chiesta la pagina dove effettuare la ricerca di un file
def searchEmpty():
    return render_template('search.html')

@app.route("/search", methods=['GET'])  # ci viene inviato il form con la stringa da ricercare
def searchPerform():
    searchKey = request.form['searchkey']
    data = "NIY!"
    return data

def kill():
    s.close()

