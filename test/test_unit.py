#!/usr/bin/env python3
import unittest
import requests
import urllib.request
from flask import Flask, url_for
from flask_testing import LiveServerTestCase
from flask_testing import TestCase

from WebUI import app


class HomePageTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        return app

    def tearDown(self):
        pass

    # ############################# TEST DA SLOGGATI ###########################################
    def test_a1_homepage(self):
        print("\n- Test Homepage")
        # Testo che nel caso siamo sloggati, venga reindirizzato a /setup
        response = self.app.get('/', follow_redirects=False)
<<<<<<< HEAD
        self.assertEqual(response.status_code, 302, "Errore, codice http sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup', "Errore, non si è stati reindirizzaticorrettamente"
                                                                      )
=======
        self.assertEqual(response.status_code, 302, "Errore,codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si è stati reindirizzaticorrettamente"
                         )
>>>>>>> develop
        # Verifico che la redirezione vada a buon fine
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Redirezione di homepage(sloggato) non è andata a buon fine")

    def test_a2_get_setup(self):
        print("\n- Test Get Setup")
        response = self.app.get('/setup', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

<<<<<<< HEAD
    # Con questo test, si porta il monkey_peer in stato loggato, da qui in poi i test fatti saranno eseguiti
    # considerando di essere loggati
    def test_a3_post_setup(self):
=======
    def test_a3_search_slogged(self):
        # Se si è sloggati e si prova a raggiungere la pagina search si viene reindirizzati in setup
        print("\n-Test slogged search..")
        response = self.app.get("/search", follow_redirects=False)
        self.assertEqual(response.status_code, 302, "Errore, codice http di ritorno sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup',
                         "Errore, non si è stati reindirizzaticorrettamente"
                         )

    # Con questo test, si porta il monkey_peer in stato loggato, da qui in poi i test fatti saranno eseguiti
    # considerando di essere loggati
    def test_a4_post_setup(self):
>>>>>>> develop
        print("\n- Test Post Setup ")
        payload = {'peer_ipv4': "127.0.0.1",
                   'peer_ipv6': "::1",
                   'peer_port': "5000",
                   'tracker_ipv4': "127.0.0.1",
                   'tracker_ipv6': "::1",
                   'tracker_port': "3000",
                   'msg': "y"
                   }
        # Testo che nel caso siamo sloggati, venga reindirizzato a /login
        response = self.app.post('/setup', data=payload, follow_redirects=False)
        self.assertEqual(302, response.status_code, "Setup post request failed")
        self.assertEqual(response.location, 'http://localhost/', "Errore, non si è stati reindirizzati " +
                         "correttamente")

        response = self.app.post('/setup', data=payload, follow_redirects=True)
        self.assertEqual(200, response.status_code, "Setup post redirect in homepage da loggati fallito")
<<<<<<< HEAD
    # ############################# FORSE CONVIENE FARE UNA FASE IN CUI IL SID RESTITUITO E' ERR o 000000.. ######
    # ############################# TEST DA LOGGATI ###########################################

    def test_b2_homepage2(self):
=======

    # ############################# FORSE CONVIENE FARE UNA FASE IN CUI IL SID RESTITUITO E' ERR o 000000.. ######
    # ############################# TEST DA LOGGATI ###########################################

    def test_b1_homepage2(self):
>>>>>>> develop
        print("\n- Test Homepage2, mostrare a display file")
        # Verifico che la redirezione vada a buon fine
        response = self.app.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 200, "Il codice http ritornato non è 200")

<<<<<<< HEAD
=======
    def test_b2_get_search(self):
        print("\n- Testing get method on Search")
        response = self.app.get('/search', follow_redirects=False)
        self.assertEqual(response.status_code, 200, "Il codice http ritornato non è 200")

    def test_b3_post_search(self):
        print("\n- Testing post method on Search")

        print("1) Ricerca di file con nome 'helmet': ")
        payload = {'filename': 'helmet'}
        response = self.app.post('/search', data=payload, follow_redirects=False)
        self.assertEqual(response.status_code, 200, "1)Il codice http ritornato non è 200")
        print("Superato!\n")

        print("2) Ricerca di tutti i file tramite '*': ")
        payload = {'filename': '*'}
        response = self.app.post('/search', data=payload, follow_redirects=False)
        self.assertEqual(response.status_code, 200, "2)Il codice http ritornato non è 200")
        print("Superato!\n")

>>>>>>> develop

if __name__ == "__main__":
    unittest.main()
