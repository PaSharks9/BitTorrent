#!/usr/bin/env python3

import unittest

from flask import template_rendered
from contextlib import contextmanager

from WebUI import app


class HomePageTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        return app

    def tearDown(self):
        pass

    @contextmanager
    def captured_templates(self):
        recorded = []

        def record(sender, template, context, **extra):
            recorded.append((template, context))

        template_rendered.connect(record, app)
        try:
            yield recorded
        finally:
            template_rendered.disconnect(record, app)

    # ############################# TEST DA SLOGGATI ###########################################
    def test_a1_homepage(self):
        print(" Test Cases da SLOGGATI")
        print("\n- Test Homepage")
        # Testo che nel caso siamo sloggati, venga reindirizzato a /setup
        response = self.app.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Errore,codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si è stati reindirizzati correttamente")

        # Verifico che la redirezione vada a buon fine
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Redirezione di homepage(sloggato) non è andata a buon fine")

    def test_a2_search(self):

        # Se si è sloggati e si prova a raggiungere la pagina search si viene reindirizzati in setup
        print("\n-Test Search")
        response = self.app.get("/search", follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Errore, codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si è stati reindirizzati correttamente")

        # Verifico che la redirezione vada a buon fine
        response = self.app.get('/search', follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Redirezione di homepage(sloggato) non è andata a buon fine")

    def test_a3_upload(self):
        print("\n-Test Upload")
        response = self.app.get("/upload", follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Errore, codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si è stati reindirizzati correttamente")

        # Verifico che la redirezione vada a buon fine
        response = self.app.get('/upload', follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Redirezione di homepage(sloggato) non è andata a buon fine")

    def test_a4_logout(self):
        print("\n- Test LogOut")
        response = self.app.get("/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Errore, codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si è stati reindirizzati correttamente")

        # Verifico che la redirezione vada a buon fine
        with self.captured_templates() as templates:
            response = self.app.get('/logout', follow_redirects=True)
            assert len(templates) == 1, "Errore, più templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Redirezione di logout non è andata a buon fine")
            self.assertEqual(template.name, "setup.html", "Errore, redirezione su una pagina diversa da setup")
            self.assertEqual(context['ipv4peer'], "127.0.0.1")

    def test_a5_download(self):
        print("\n- Test Download")
        response = self.app.get("/download", follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Errore, codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si è stati reindirizzati correttamente")

        # Verifico che la redirezione vada a buon fine
        with self.captured_templates() as templates:
            response = self.app.get('/logout', follow_redirects=True)
            assert len(templates) == 1, "Errore, più templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Redirezione di logout non è andata a buon fine")
            self.assertEqual(template.name, "setup.html", "Errore, redirezione su una pagina diversa da setup")
            self.assertEqual(context['ipv4peer'], "127.0.0.1")

    def test_a6_setup(self):
        payload = {'peer_ipv4': "127.0.0",
                   'peer_ipv6': "::1",
                   'peer_port': "5000abc",
                   'tracker_ipv4': "127.0.0.1",
                   'tracker_ipv6': ":af:1",
                   'tracker_port': "3000",
                   'msg': "y"
                   }
        payload2 = {'peer_ipv4': "127.0.0.1",
                    'peer_ipv6': "::1",
                    'peer_port': "5000",
                    'tracker_ipv4': "127.0.0.1",
                    'tracker_ipv6': "::1",
                    'tracker_port': "3000",
                    'msg': "y"
                    }
        # Test di get su setup
        print("\n- Test Get Setup")
        response = self.app.get('/setup', follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Error code in test di get su setup, codice ricevuto: " +
                         str(response.status_code) + " invece di 200")

        # Test di post su setup con parametri sbagliati
        print("\n- Test Post Setup with wrong parameters")
        with self.captured_templates() as templates:
            response = self.app.post('/setup', data=payload, follow_redirects=True)
            self.assertEqual(response.status_code, 200, "Error code di post su setup, codice ricevuto: "
                             + str(response.status_code) + " invece di 200")
            assert len(templates) == 1, "Errore, più templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(template.name, "setup.html", "Errore, redirezione su una pagina diversa da setup")

            # Vado a controllare che effettivamente i parametri sbagliati vengono messi a : ""
            self.assertEqual(context['log'], "false", "Errore, log dovrebbe essere false invece di: " + context['log'])
            self.assertEqual(context['portpeer'], "",
                             "Errore nella correzione peer_port, valore: " + context['portpeer'])
            self.assertEqual(context['ipv4peer'], "", "Errore nella correzione del peer_ipv4")
            self.assertEqual(context['ipv6tracker'], "", "Errore nella correzione del tracker_ipv6")

        # Test con i parametri giusti
        print("\n- Test Post Setup with right param")
        response = self.app.post('/setup', data=payload2, follow_redirects=False)
        self.assertEqual(302, response.status_code, "Setup post request failed")
        self.assertEqual(response.location, 'http://localhost/', "Errore, non si è stati reindirizzati " +
                         "correttamente")

        # Verifico che la redirezione vada effettivamente verso '/', con questa parte si va anche a loggarsi
        response = self.app.post('/setup', data=payload2, follow_redirects=True)
        self.assertEqual(200, response.status_code, "Setup post redirect in homepage da loggati fallito")

        print("\n TEST DA LOGGATI ")
        # Se si va in Setup con post vuol dire che ci si sta sloggando, quindi vado a reindirizzare su /logout
        print("\n- Test redirect to Logout from Setup")
        response = self.app.post('/setup', data=payload2, follow_redirects=False)
        self.assertEqual(302, response.status_code, "Setup post request failed")
        self.assertEqual(response.location, 'http://localhost/logout', "Errore, non si è stati reindirizzati " +
                         "correttamente")

        # Verifico che la redirezione per sloggarsi vada a buon fine
        response = self.app.post('/setup', data=payload2, follow_redirects=True)
        self.assertEqual(200, response.status_code, "Error in status_code")

    # ############################# FORSE CONVIENE FARE UNA FASE IN CUI IL SID RESTITUITO E' ERR o 000000.. ######
    # ############################# TEST DA LOGGATI ###########################################

    def test_b1_homepage(self):
        # Test di post su setup da loggati, dovrebbe essere visto come un logout ed essere reindirizzati su /logout
        print("\n- Test get Homepage")
        with self.captured_templates() as templates:
            response = self.app.get('/', follow_redirects=False)
            assert len(templates) == 1, "Errore, più templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(200, response.status_code, "Wrong status code received ")
            self.assertEqual(context['data'], [["abcdefghiasmckaldkfideldlsopie32"], ["100"], ["5"], ["10"]])
            self.assertEqual(context['sid'], "0123456789123456")

    def test_b2_search(self):
        print("\n- Testing get method on Search")
        with self.captured_templates() as templates:
            response = self.app.get('/search', follow_redirects=False)
            assert len(templates) == 1, "Errore, più templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Il codice http ritornato non è 200")
            self.assertEqual(context['data'], "", "Errore, data deve essere: "" ")

        print("\n- Testing post method on Search")

        print("1) Ricerca di file con nome 'helmet': ")
        payload = {'filename': 'helmet'}
        with self.captured_templates() as templates:
            response = self.app.post('/search', data=payload, follow_redirects=False)
            assert len(templates) == 1, "Errore, più templates per una stessa chiamata"
            template, context = templates[0]
            # Verifico che i dati vengano splittati correttamente
            self.assertEqual(context['data'], ["e11f7b6e50eb65e311a591a244210c69", "helmet", '100', '10'])
            self.assertEqual(response.status_code, 200, "1)Il codice http ritornato non è 200")
            print("Superato!\n")

        print("2) Ricerca di tutti i file tramite '*': ")
        payload = {'filename': '*'}
        response = self.app.post('/search', data=payload, follow_redirects=False)
        self.assertEqual(response.status_code, 200, "2)Il codice http ritornato non è 200")
        print("Superato!\n")

    def test_b3_upload(self):
        path = '/home/luca/Scrivania/BitTorrent/test'
        monkey_file = open(path + "/monkeyFile.jpg", 'rb')
        payload1 = {
            'descrizione': 'filevuoto',
            'elemento': monkey_file
        }
        with self.captured_templates() as templates:
            print("\n- Testing get method on Upload")
            response = self.app.get('/upload', follow_redirects=False)
            assert len(templates) == 1, "Errore, più templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Il codice http ritornato non è 200")
            self.assertEqual(context['message'], "", "Il messaggio nella get deve essere '' ")

            print("\n- Testing post method on Upload")
            response = self.app.post('/upload', data=payload1, follow_redirects=False)
            assert len(templates) == 2, "Errore, più templates per una stessa chiamata"
            template, context = templates[1]
            self.assertEqual(response.status_code, 200, "Il codice http ritornato non è 200")
            self.assertEqual(context['load'], 'y', "Errore nel messaggio di caricamento")


if __name__ == "__main__":
    unittest.main()
