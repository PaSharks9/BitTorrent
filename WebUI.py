import socket, os
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
        print("SID: " + sid)
        return False
    else:
        print("SID: " + sid)
        return sid


@app.route("/")
def homepage():
    # Cerco impostazione per il setup
    ips = request.args.get('ips')
    sid = logged()
    if sid is False:
        # return redirect("/setup")
        return render_template('home.html', sid=sid)

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
        print(dataLists)
    return render_template('home.html', data=dataLists, sid=sid)


@app.route("/setup", methods=['GET', 'POST'])
def setup():
    if request.method == "GET":
        s.sendall("GETP".encode('utf-8'))
        data = recvUntil(s, "%").decode('utf-8')
        sid = logged()
        if data == "":
            return render_template('setup.html', ipv4peer="", ipv6peer="", portpeer="", ipv4tracker="", ipv6tracker="",
                                   porttracker="", msg="y")
        else:  # se peer.py ha letto dei parametri dal file di configurazione allora li uso per pre-compilare i campi
            # da inserire
            lista = data.split(',')
            return render_template('setup.html', ipv4peer=lista[0], ipv6peer=lista[1], portpeer=lista[2],
                                   ipv4tracker=lista[3], ipv6tracker=lista[4], porttracker=lista[5], log=sid)

    if request.method == "POST":
        data = "SETP" + str(request.form['peer_ipv4']) + ','
        data = data + str(request.form['peer_ipv6']) + ','
        data = data + str(request.form['peer_port']) + ','
        data = data + str(request.form['tracker_ipv4']) + ','
        data = data + str(request.form['tracker_ipv6']) + ','
        data = data + str(request.form['tracker_port']) + '%'

        s.sendall(data.encode('utf-8'))
        data = recvUntil(s, "%").decode('utf-8')
        return redirect('/login')


@app.route("/login")
def login():
    s.sendall("LOGI".encode('utf-8'))
    data = recvUntil(s, "%").decode('utf-8')
    if data == "0000000000000000":
        return redirect('/')
    elif data == "ERR":
        return redirect('/')
    else:
        return redirect('/')


@app.route("/search", methods=['GET', 'POST'])
def search():
    if logged() is False:
        return redirect("/setup")

    if request.method == "GET":
        return render_template('search.html', data="", sid=logged())

    if request.method == "POST":
        searchKey = "FIND"
        if len(request.form['searchkey']) < 20:  # se "research" è più corta di 20 caratteri
            searchKey = searchKey + (request.form['searchkey']).ljust(20)
        else:
            temp = request.form['searchkey']
            searchKey = searchKey + temp[0:20]  # prendo i primi 20 caratteri della chiave

        s.sendall(searchKey.encode('utf-8'))
        temp = recvUntil(s, "%").decode('utf-8')

        risultati = temp.split(',')  # da formato CSV restituisce una lista
        return render_template('search.html', data=risultati, sid=logged())


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
                return render_template('upload.html', message='Si sta già condividendo il file selezionato!')
            elif data == "FTB":
                return render_template('upload.html',
                                       message="La dimesione in byte del file dev'essere di massimo 10 cifre!")
            else:
                lista = data.split(',')
                data = "Caricamento avvenuto con successo.</br>MD5: " + lista[0] + "</br>Dimensione parti: " + lista[
                    1] + "</br></br><a href='/'>Torna alla homepage</a>"
            return data


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


@app.route("/download", methods=['GET'])
def download():
    if logged() is False:
        return redirect('/login')
    if logged() is False:
        return redirect("/setup")

    data = "DOWN" + request.args.get('md5') + ',' + request.args.get('name') + ',' + str(
        request.args.get('size')) + ',' + str(request.args.get('part')) + "%"

    s.sendall(data.encode('utf-8'))

    return render_template('download.html')


def kill():
    s.close()


if __name__ == "__main__":
    app.run(debug=True)
    s.close()
