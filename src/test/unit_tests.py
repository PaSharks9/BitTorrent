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

    # ############################# TEST DA LOGGATI ###########################################

    def test_b1_homepage(self):
        # Test di post su setup da loggati, dovrebbe essere visto come un logout ed essere reindirizzati su /logout
        print("----- FILE: unit_tests.py -----")
        print("\n- Test get Homepage")
        with self.captured_templates() as templates:
            response = self.app.get('/', follow_redirects=False)
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(200, response.status_code, "Wrong status code received ")
            self.assertEqual(context['data'], [["abcdefghiasmckaldkfideldlsopie32"], ["100"], ["5"], ["10"]])
            self.assertEqual(context['sid'], "0123456789123456")

    def test_b2_search(self):
        print("\n- Test di Search: ")
        print("\n\t1- Testing get method on Search")
        with self.captured_templates() as templates:
            response = self.app.get('/search', follow_redirects=False)
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Il codice http ritornato non e 200")
            self.assertEqual(context['data'], "", "Errore, data deve essere: "" ")
            self.assertEqual(context['sid'], "0123456789123456")

        print("\n\t2- Testing post method on Search")
        print("\t\t1) Ricerca di file con nome 'helmet': ")
        payload = {'filename': 'helmet'}
        with self.captured_templates() as templates:
            response = self.app.post('/search', data=payload, follow_redirects=False)
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            # Verifico che i dati vengano splittati correttamente
            self.assertEqual(context['data'], [["e11f7b6e50eb65e311a591a244210c69", "helmet", '100', '10']])
            self.assertEqual(response.status_code, 200, "1)Il codice http ritornato non e 200")

        print("\t\t2) Ricerca di tutti i file tramite '*': ")
        payload = {'filename': '*'}
        response = self.app.post('/search', data=payload, follow_redirects=False)
        self.assertEqual(response.status_code, 200, "2)Il codice http ritornato non e 200")

    def test_b3_upload(self):
        path = '/home/luca/Scrivania/BitTorrent/src/test'
        monkey_file = open(path + "/monkeyFile.jpg", 'rb')
        payload1 = {
            'descrizione': 'filevuoto',
            'elemento': monkey_file
        }
        monkey_file2 = open(path + "/monkeyFile.jpg", 'rb')
        payload2 = {'descrizione': 'file vuoto',
                    'elemento': monkey_file2
                    }

        print("\n- Test di Upload")
        with self.captured_templates() as templates:
            print("\n\t1- Testing get method on Upload")
            response = self.app.get('/upload')
            assert len(templates) == 1, "Errore, piu di 1 templates per chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "1)Il codice http ritornato non e 200")
            self.assertEqual(context['message'], "", "Il messaggio nella get deve essere '' ")

            print("\n\t2- Testing the upload of a file that's already shared")
            response = self.app.post('/upload', data=payload1)
            assert len(templates) == 2, "Errore, più di 2 templates per la chiamata"
            template, context = templates[1]
            self.assertEqual(response.status_code, 200, "2)Il codice http ritornato non e 200")
            self.assertEqual(context['message'], 'Si sta gia condividendo il file selezionato!',
                             "Errore nel messaggio di caricamento")

            print("\n\t3- Testing post method on Upload")
            response = self.app.post('/upload', data=payload2)
            assert len(templates) == 3, "Errore, piu di 3 templates per la chiamata"
            template, context = templates[2]
            self.assertEqual(response.status_code, 200, "3)Il codice http ritornato non e 200")
            self.assertEqual(context['load'], 'y', "Errore nel messaggio di caricamento")

    def test_b4_logout(self):
        print("\n - Test Logout")

        with self.captured_templates() as templates:
            print("\n\t 1- Case where the user is sharing a file and he wants to logout. He can't")
            response = self.app.get('/logout')
            assert len(templates) == 1, "Errore, piu templates per una stessa chiamata"
            template, context = templates[0]
            self.assertEqual(response.status_code, 200, "Errore, mancata visualizzazione di logout.html")
            self.assertEqual(template.name, 'logout.html', 'Errore, visualizzata pagina diversa da logout.html')
            self.assertEqual(context['result'], "ko")

            print("\n\t 2- Case where the user is logged and he doesn't share any file. He can logout")

            response = self.app.get('/logout')
            assert len(templates) == 2, "Errore, piu di 2 templates per una stessa chiamata"
            template, context = templates[1]
            self.assertEqual(response.status_code, 200, "Errore, mancata visualizzazione di logout.html")
            response = self.app.get('/logout', follow_redirects=True)
            self.assertEqual(response.status_code, 200, "Redirezione di logout non e andata a buon fine")
            self.assertEqual(template.name, 'logout.html', 'Errore, visualizzata pagina diversa da logout.html')
            self.assertEqual(context['result'], "ok")

            print("\n\n-------- Test Eseguiti --------\n\n")


if __name__ == "__main__":
    unittest.main()
