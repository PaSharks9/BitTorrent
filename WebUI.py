import socket, os, ipaddress

from flask import Flask, render_template, request, redirect, url_for


# from werkzeug import secure_filename

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

        if (temp == pattern.encode('utf-8')):  # se ho letto il terminatore
            break  # ho finito di leggere
        else:
            letto += temp
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
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, "downloads")


def logged():
    s.sendall("LOG?".encode('utf-8'))
    sid = recvUntil(s, '%').decode('utf-8')

    if sid == "False":
        return False
    else:
        return sid


@app.route("/")
def homepage():
    # Cerco impostazione per il setup
    ips = request.args.get('ips')
    sid = logged()
    if sid is False:
        return redirect("/setup")

    s.sendall("HOME".encode('utf-8'))
    data = recvUntil(s, "%").decode('utf-8')
    if data == "":
        dataLists = ""
    else:
        dataLists = []
        data = data.split('|')
        for element in data:
            fileInfo = element.split(':')
            if '' in fileInfo:
                dataLists.append(fileInfo.remove(''))
            else:
                dataLists.append(fileInfo)
        # print(dataLists)
        print("sid: " + str(sid))
        print("dati: " + str(dataLists))
    return render_template('home.html', data=dataLists, sid=sid)


@app.route("/setup", methods=['GET', 'POST'])
def setup():
    if request.method == "GET":
        s.sendall("GETP".encode('utf-8'))
        data = recvUntil(s, "%").decode('utf-8')

        sid = logged()
        if sid is False:
            loggato = "false"
        else:
            loggato = "true"

        if data == "":
            return render_template('setup.html', ipv4peer="", ipv6peer="", portpeer="", ipv4tracker="", ipv6tracker="",
                                   porttracker="", msg="y", log=loggato)
        else:  # se peer.py ha letto dei parametri dal file di configurazione allora li uso per pre-compilare i campi
            # da inserire
            lista = data.split(',')
            return render_template('setup.html', ipv4peer=lista[0], ipv6peer=lista[1], portpeer=lista[2],
                                   ipv4tracker=lista[3], ipv6tracker=lista[4], porttracker=lista[5], log=loggato)

    if request.method == "POST":
        if logged() is False:  # se non siamo gia loggati

            peer_v4 = str(request.form['peer_ipv4'])
            peer_v6 = str(request.form['peer_ipv6'])
            peer_port = str(request.form['peer_port'])
            tracker_v4 = str(request.form['tracker_ipv4'])
            tracker_v6 = str(request.form['tracker_ipv6'])
            tracker_port = str(request.form['tracker_port'])

            # Eseguo il controllo sintattico dei parametri che mi arrivano dal form html
            try:
                ipaddress.ip_address(peer_v4)
            except ValueError:
                peer_v4 = ""

            try:
                ipaddress.ip_address(peer_v6)
            except ValueError:
                peer_v6 = ""

            try:
                # oltre al test sul valore numerico c'e anche il test (implicito) che sia un valore
                # numerico grazie alla funzione int()
                if (int(peer_port) > 65535) or (int(peer_port) < 0):
                    peer_port = ""
            except ValueError:
                peer_port = ""

            try:
                ipaddress.ip_address(tracker_v4)
            except ValueError:
                tracker_v4 = ""

            try:
                ipaddress.ip_address(tracker_v6)
            except ValueError:
                tracker_v6 = ""

            try:
                # oltre al test sul valore numerico c'e anche il test (implicito) che sia un valore
                # numerico grazie alla funzione int()
                if (int(tracker_port) > 65535) or (int(tracker_port) < 0):
                    tracker_port = ""
            except ValueError:
                tracker_port = ""

            # Se almeno uno dei parametri e stato reso "" dai controlli
            # allora devo rimandare l'utente alla pagina /setup vuotando i campi (sintatticamente) errati
            if (peer_v4 == "") or (peer_v6 == "") or (peer_port == "") or (tracker_v4 == "") or (tracker_v6 == "") or (
                    tracker_port == ""):
                return render_template('setup.html', ipv4peer=peer_v4, ipv6peer=peer_v6, portpeer=peer_port,
                                       ipv4tracker=tracker_v4, ipv6tracker=tracker_v6, porttracker=tracker_port,
                                       log="false")

            # Se siamo arrivati qui allora il controllo sintattico dei parametri e andato
            # a buon fine quindi possiamo procedere.
            data = "SETP" + peer_v4 + ',' + peer_v6 + ',' + peer_port + ',' + tracker_v4 + ',' + tracker_v6 + ',' + tracker_port + '%'

            s.sendall(data.encode('utf-8'))
            data = recvUntil(s, "%").decode('utf-8')

            s.sendall("LOGI".encode('utf-8'))
            data = recvUntil(s, "%").decode('utf-8')

            if data == "0000000000000000" or data == "ERR":
                return render_template('error.html', code=data)
            else:
                return redirect("/")

        else:  # se siamo gia loggati allora stiamo chiedendo il logout
            return redirect("/logout")


@app.route("/search", methods=['GET', 'POST'])
def search():
    if logged() is False:
        return redirect("/setup")

    if request.method == "GET":
        return render_template('search.html', data="", sid=logged())

    if request.method == "POST":
        searchKey = "FIND"
        if len(request.form['filename']) < 20:  # se "research" e piu corta di 20 caratteri
            searchKey = searchKey + (request.form['filename']).ljust(20)
        else:
            temp = request.form['filename']
            searchKey = searchKey + temp[0:20]  # prendo i primi 20 caratteri della chiave

        s.sendall(searchKey.encode('utf-8'))
        temp = recvUntil(s, "%").decode('utf-8')
        risultati = temp.split(',')  # da formato CSV restituisce una lista
        print("risultati: " + str(risultati))
        res = []
        part = []
        i = 0
        for el in risultati:
            if i < 3:
                if i == 1:
                    part.append(el.strip())
                else:
                    part.append(el)
                i += 1
            else:
                i = 0
                part.append(el)
                res.append(part)
                part = []

        return render_template('search.html', data=res, sid=logged())


@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if logged() is False:
        return redirect("/setup")

    if request.method == "GET":
        return render_template('upload.html', message='')

    if request.method == "POST":
        f = request.files['elemento']
        nome = f.filename

        if nome == '':
            return render_template('upload.html', message='Prego selezionare un file esistente!')
        else:
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], nome))
            data = "UPLD" + os.path.join(app.config['UPLOAD_FOLDER'], nome) + ',' + str(
                request.form['descrizione']) + '%'
            s.sendall(data.encode('utf-8'))

            data = recvUntil(s, "%").decode('utf-8')

            if data == "ERR":
                data = "Si e' verificato un errore durante il caricamento (tra peer e tracker).</br>Si prega di " \
                       "riprovare... "
            elif data == "FNF":
                return render_template('upload.html', message='Impossibile aprire il file!')
            elif data == "FAS":
                return render_template('upload.html', message='Si sta gia condividendo il file selezionato!')
            elif data == "FTB":
                return render_template('upload.html',
                                       message="La dimesione in byte del file dev'essere di massimo 10 cifre!")
            else:
                lista = data.split(',')
                return render_template('upload.html', md5=lista[0], dim=lista[1], load="y")


@app.route("/logout")
def logout():
    if logged() is False:
        return redirect("/setup")

    s.sendall("LOGO".encode('utf-8'))
    data = recvUntil(s, "%").decode('utf-8')

    if data == "OK":
        return "Logout successfully performed."
    else:
        return "Logout failed."


@app.route("/download")
def download():
    if logged() is False:
        # print("Dentro logged() is false")
        return redirect('/setup')
    '''data = "DOWN" + request.form['md5'] + ',' + request.form['descrizione'] + ',' + str(
        request.form['dimFile']) + ',' + str(request.form['dimParti']) + "%"'''
    print(request.args)
    data = "DOWN" + str(request.args.get('md5')) + ',' + str(request.args.get('name')) + ',' + str(request.args.get('size')) + ',' + str(request.args.get('part')) + "%"
    print("data: " + str(data))
    s.sendall(data.encode('utf-8'))
    data = recvUntil(s, "%").decode('utf-8')
    return render_template('download.html', data=request.args.get('name'))


def kill():
    s.close()


if __name__ == "__main__":
    app.run(debug=False)
    s.close()
