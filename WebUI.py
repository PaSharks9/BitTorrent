import socket
from flask import Flask, render_template, request


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
        temp = recvExact(miaSocket, len(pattern))
        letto += temp

        if (temp == pattern.encode('utf-8')):  # se ho letto il terminatore "�"
            break  # ho finito di leggere
    return letto


# Programma
HOST = '127.0.0.1'  # The remote host
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    PORT = int(input("Digitare il numero di porta a cui collegarsi"))
    s.connect((HOST, PORT))
except:
    print("ERROR: Wrong port number. Please check, than retry...")

app = Flask(__name__)


@app.route("/")
def homepage():
    # s.sendall("HOME".encode('utf-8'))
    # data = recvUntil(s,"%").decode('utf-8')
    return render_template('home.html', active="True")


@app.route("/search", methods=['GET', 'POST'])
def search():
    if request.method == "GET":
        return render_template('search.html', active="True")

    if request.method == "POST":
        searchKey = "FIND"
        if len(request.form['searchkey']) < 20:  # se "research" è più corta di 20 caratteri
            searchKey = searchKey + request.form['searchkey'] + ' ' * len(request.form['searchkey'])
        else:
            temp = request.form['searchkey']
            searchKey = searchKey + temp[0:20]  # prendo i primi 20 caratteri della chiave

        s.sendall(searchKey.encode('utf-8'))

        temp = recvUntil(s, "%").decode('utf-8')
        risultati = temp.split(',')  # da formato CSV restituisce una lista

        data = '<table style="width:100%"><tr><th>Md5 file</th><th>Descrizione</th><th>Dimensione ' \
               'file</th><th>Dimensione parti</th></tr> '
        for index in range(0, len(risultati) / 4):
            data = data + '<tr>'
            data = data + '<td>' + risultati[4 * index] + '</td>'
            data = data + '<td>' + risultati[4 * index + 1] + '</td>'
            data = data + '<td>' + risultati[4 * index + 2] + '</td>'
            data = data + '<td>' + risultati[4 * index + 3] + '</td>'
            data = data + '</tr>'
        data = data + '</table>'

        return data


@app.route("/download", methods=['POST'])
def download():
    md5 = "Qualcosa"
    data = "DOWN" + md5
    s.sendall(data.encode('utf-8'))

    data = recvUntil(s, "%").decode('utf-8')
    if (data == "OK"):  data = "Download avviato correttamente. TORNA ALLA HOMEPAGE"
    if (data == "KO"):  data = "Si e' verificato un errore nell'avvio del download. TORNA ALLA HOMEPAGE"

    return data


def kill():
    s.close()


if __name__ == "__main__":
    app.run(debug=True)
