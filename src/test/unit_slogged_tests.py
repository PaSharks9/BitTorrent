#!/usr/bin/env python3

from flask import template_rendered
from contextlib import contextmanager

import unittest

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
        print("----- FILE: unit_slogged_tests.py -----")
        print("TEST DA SLOGGATI")
        print("\n- Test Homepage")

        # Testo che nel caso siamo sloggati, venga reindirizzato a /setup
        response = self.app.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Redirezione di homepage(sloggato) non e andata a buon fine")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si e stati reindirizzati  correttamente")

        # Verifico che la redirezione vada a buon fine
        with self.captured_templates() as templates:
            response = self.app.get('/', follow_redirects=True)
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Redirezione di homepage(sloggato) non e andata a buon fine")
            self.assertEqual(template.name, "setup.html", "Errore, redirezione su una pagina diversa da setup")

    def test_a2_search(self):

        # Se si e sloggati e si prova a raggiungere la pagina search si viene reindirizzati in setup
        print("\n- Test Search")
        response = self.app.get("/search", follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Errore, codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si e stati reindirizzati correttamente")

        # Verifico che la redirezione vada a buon fine
        with self.captured_templates() as templates:
            response = self.app.get('/search', follow_redirects=True)
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Redirezione di homepage(sloggato) non e andata a buon fine")
            self.assertEqual(template.name, "setup.html", "Errore, redirezione su una pagina diversa da setup")

    def test_a3_upload(self):
        print("\n- Test Upload")
        response = self.app.get("/upload", follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Errore, codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si e stati reindirizzati correttamente")

        # Verifico che la redirezione vada a buon fine
        with self.captured_templates() as templates:
            response = self.app.get('/upload', follow_redirects=True)
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Redirezione di homepage(sloggato) non e andata a buon fine")
            self.assertEqual(template.name, "setup.html", "Errore, redirezione su una pagina diversa da setup")

    def test_a4_logout(self):
        print("\n- Test LogOut")
        response = self.app.get("/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Errore, codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si e stati reindirizzati correttamente")

        # Verifico che la redirezione vada a buon fine
        with self.captured_templates() as templates:
            response = self.app.get('/logout', follow_redirects=True)
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Redirezione di logout non e andata a buon fine")
            self.assertEqual(template.name, "setup.html", "Errore, redirezione su una pagina diversa da setup")
            self.assertEqual(context['ipv4peer'], "127.0.0.1")

    def test_a5_download(self):
        print("\n- Test Download")
        response = self.app.get("/download", follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Errore, codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si e stati reindirizzati correttamente")

        # Verifico che la redirezione vada a buon fine
        with self.captured_templates() as templates:
            response = self.app.get('/logout', follow_redirects=True)
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Redirezione di logout non e andata a buon fine")
            self.assertEqual(template.name, "setup.html", "Errore, redirezione su una pagina diversa da setup")
            self.assertEqual(context['ipv4peer'], "127.0.0.1")

    def test_a6_sid_error(self):
        print("\n- Test Sid Error")
        payload = {'peer_ipv4': "127.0.0.1",
                   'peer_ipv6': "::1",
                   'peer_port': "5000",
                   'tracker_ipv4': "127.0.0.1",
                   'tracker_ipv6': "::1",
                   'tracker_port': "3000",
                   'msg': "y"
                   }
        # Controllo che la redirezione funzioni
        with self.captured_templates() as templates:
            response = self.app.post('/setup', data=payload, follow_redirects=True)
            self.assertEqual(response.status_code, 200, "Error code di post su setup, codice ricevuto: "
                             + str(response.status_code) + " invece di 200")
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(template.name, 'error.html', 'Errore di redirezione su pagina diversa da error')
            assert context['code'] in ['0000000000000000', 'ERR']

    def test_a7_setup(self):
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
        print("\n- Test Setup")
        print("\n\t1- Test Get Setup")
        response = self.app.get('/setup', follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Error code in test di get su setup, codice ricevuto: " +
                         str(response.status_code) + " invece di 200")

        # Test di post su setup con parametri sbagliati
        print("\n\t2- Test Post Setup with wrong parameters")
        with self.captured_templates() as templates:
            response = self.app.post('/setup', data=payload, follow_redirects=True)
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Error code di post su setup, codice ricevuto: "
                             + str(response.status_code) + " invece di 200")
            self.assertEqual(template.name, "setup.html", "Errore, redirezione su una pagina diversa da setup")

            # Vado a controllare che effettivamente i parametri sbagliati vengono messi a : ""
            self.assertEqual(context['log'], "false", "Errore, log dovrebbe essere false invece di: " + context['log'])
            self.assertEqual(context['portpeer'], "",
                             "Errore nella correzione peer_port, valore: " + context['portpeer'])
            self.assertEqual(context['ipv4peer'], "", "Errore nella correzione del peer_ipv4")
            self.assertEqual(context['ipv6tracker'], "", "Errore nella correzione del tracker_ipv6")

        # Test con i parametri giusti, qui viene effettuato il login
        print("\n\t3- Test Post Setup with right param")
        response = self.app.post('/setup', data=payload2, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, 'http://localhost/')

        # Controllo che la redirezione funzioni
        response = self.app.post('/setup', data=payload2, follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Error code di post su setup, codice ricevuto: "
                         + str(response.status_code) + " invece di 200")

        print("\n TEST DA LOGGATI")
        # Se eseguo una post su setup da loggati e da interpretare come una logout,
        # verifico che il reindirizzamento sia corretto
        print("\n\t[Test di Setup]4- Verifico la logout da setup\n\n")
        response = self.app.post('/setup', data=payload2, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, 'http://localhost/logout')


if __name__ == "__main__":
    unittest.main()
