import socket
from flask import Flask, render_template, request, redirect

logged = False

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

        if (temp == pattern.encode('utf-8')):   # se ho letto il terminatore
            break  # ho finito di leggere
        else:
            letto += temp
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

@app.route("/upload", methods=['GET','POST'])
def upload():
    if(logged is False):
        return redirect('/login')
        
    if request.method == "GET":
        return render_template('upload.html', message='')

    if request.method == "POST":
        file = request.files['file']
        
        if(file.filename == ''):
            return render_template('upload.html', message='Prego selezionare un file esistente!')
        else:
            data = "UPLD" + str(file.filename) + ',' + str(request.form['descrizione']) + '%'
            s.sendall(data.encode('utf-8'))
        
            data = recvUntil(s,"%").decode('utf-8')
             
            if(data == "ERR"):
                data = "Si e' verificato un errore durante il caricamento (tra peer e tracker).</br>Si prega di riprovare..."
            elif(data == "FNF"):
                return render_template('upload.html', message='Impossibile aprire il file!')
            elif(data == "FAS"):
                return render_template('upload.html', message='Si sta già condividendo il file selezionato!')
            elif(data == "FTB"):
                return render_template('upload.html', message="La dimesione in byte del file dev'essere di massimo 10 cifre!")
            else:
                lista = data.split(',')
                data = "Caricamento avvenuto con successo.</br>MD5: " + lista[0] + "</br>Dimensione parti: " + lista[1] + "</br></br><a href='/'>Torna alla homepage</a>"
            return data

@app.route("/setup", methods=['GET','POST'])
def setup():
    if request.method == "GET":
        s.sendall("GETP".encode('utf-8'))
        data = recvUntil(s,"%").decode('utf-8')
        
        if(data == ""):
            return render_template('setup.html', ipv4peer="", ipv6peer="", portpeer="", ipv4tracker="", ipv6tracker="", porttracker="")
        else:   # se peer.py ha letto dei parametri dal file di configurazione allora li uso per pre-compilare i campi da inserire
            lista = data.split(',')
            return render_template('setup.html', ipv4peer=lista[0], ipv6peer=lista[1], portpeer=lista[2], ipv4tracker=lista[3], ipv6tracker=lista[4], porttracker=lista[5])
    
    if request.method == "POST":
        data = "SETP"   + str(request.form['peer_ipv4']) + ','
        data = data     + str(request.form['peer_ipv6']) + ','
        data = data     + str(request.form['peer_port']) + ','
        data = data     + str(request.form['tracker_ipv4']) + ','
        data = data     + str(request.form['tracker_ipv6']) + ','
        data = data     + str(request.form['tracker_port'])

        s.sendall("SETP".encode('utf-8'))
        data = recvUntil(s,"%").decode('utf-8')
        return data

@app.route("/login")
def login():
    s.sendall("LOGI".encode('utf-8'))
    data = recvUntil(s,"%").decode('utf-8')

    if(data == "0000000000000000"):
        return "Login failed (tracker returned all-zeroes sid). Retry..."
    elif(data == "ERR"):
        return "Login failed due tracker's socket issues. Retry..."
    else:
        logged = True
        return "Login success.</br>Sid: " + str(data)

@app.route("/logout")
def logout():
    if(logged is False):
        return redirect('/login')

    s.sendall("LOGO".encode('utf-8'))
    data = recvUntil(s,"%").decode('utf-8')

    if(data == "OK"):
        logged = False
        return "Logout successfully performed."
    else:
        return "Logout failed."

@app.route("/")
def homepage():
    if(logged is False):
        return redirect('/login')

    s.sendall("HOME".encode('utf-8'))
    data = recvUntil(s,"%").decode('utf-8')

    if(data == ""): data = 'Al momento non si possiede alcuna parte di alcun file.<br><a href="/search">Cerca un file</a>' 
    return data

@app.route("/search", methods=['GET','POST'])
def search():
    if(logged is False):
        return redirect('/login')

    if request.method == "GET":
        return render_template('search.html')
    
    if request.method == "POST":
        searchKey = "FIND"
        if len(request.form['searchkey']) < 20:  # se "research" è più corta di 20 caratteri
            searchKey = searchKey + (request.form['searchkey']).ljust(20)
        else:  
            temp = request.form['searchkey']
            searchKey = searchKey + temp[0:20]  # prendo i primi 20 caratteri della chiave

        s.sendall(searchKey.encode('utf-8'))

        temp = recvUntil(s,"%").decode('utf-8')
        
        if(temp == ""):
            data = "Nessun file corrisponde alla chiave di ricerca."
        else:
            risultati = temp.split(',') # da formato CSV restituisce una lista
            
            data = '<table style="width:100%"><tr><th>Md5 file</th><th>Descrizione</th><th>Dimensione file</th><th>Dimensione parti</th></tr>'
            for index in range(0, int((len(risultati)-1)/4)):
                data = data + '<tr>'

                data = data + '<td style="text-align:center"><a href="/download?md5=' + risultati[4*index] + '&name=' + risultati[4*index +1] + '&size=' + risultati[4*index +2] + '&part=' + risultati[4*index +3] + '">' + risultati[4*index] + '</a></td>'
                data = data + '<td style="text-align:center">' + risultati[4*index +1] + '</td>'
                data = data + '<td style="text-align:center">' + risultati[4*index +2] + '</td>'
                data = data + '<td style="text-align:center">' + risultati[4*index +3] + '</td>'
                data = data + '</tr>'
            data = data + '</table>'
               
        return data

@app.route("/download", methods=['GET'])
def download():
    if(logged is False):
        return redirect('/login')

    data = "DOWN" + request.args.get('md5') + ',' + request.args.get('name') + ',' + str(request.args.get('size')) + ',' + str(request.args.get('part')) + "%"
    
    s.sendall(data.encode('utf-8'))

    data = recvUntil(s,"%").decode('utf-8')

    if(data == "OK"):   data = "Download eseguito correttamente."
    else:               data = "Si è verificato un problema durante il download."
    data = data + "<br><br><a href='/'>Torna alla homepage</a>"
    
    return data

def kill():
    s.close()

