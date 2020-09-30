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
        self.assertEqual(response.status_code, 302, "Errore, codice http sbagliato")
        self.assertEqual(response.location, 'http://localhost/setup', "Errore, non si è stati reindirizzaticorrettamente"
                                                                      )
        # Verifico che la redirezione vada a buon fine
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Redirezione di homepage(sloggato) non è andata a buon fine")

    def test_a2_get_setup(self):
        print("\n- Test Get Setup")
        response = self.app.get('/setup', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    # Con questo test, si porta il monkey_peer in stato loggato, da qui in poi i test fatti saranno eseguiti
    # considerando di essere loggati
    def test_a3_post_setup(self):
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
    # ############################# FORSE CONVIENE FARE UNA FASE IN CUI IL SID RESTITUITO E' ERR o 000000.. ######
    # ############################# TEST DA LOGGATI ###########################################

    def test_b2_homepage2(self):
        print("\n- Test Homepage2, mostrare a display file")
        # Verifico che la redirezione vada a buon fine
        response = self.app.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 200, "Il codice http ritornato non è 200")


if __name__ == "__main__":
    unittest.main()
