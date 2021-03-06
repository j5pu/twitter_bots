# -*- coding: utf-8 -*-

import os
from PIL import Image
import requests
import simplejson
import time
from core.managers import mutex
from core.scrapper.utils import mkdir_if_not_exists
from twitter_bots import settings
from ...scrapper.captcha_resolvers import deathbycaptcha

DEFAULT_TIMEOUT = 30
POLL_INTERVAL = 5
MAX_REQ_ATTEMPTS = 5


class CaptchaResolver(object):
    def __init__(self, scrapper):
        self.scrapper = scrapper

    def crop_captcha(self, img_el, captcha_filepath):
        # puesto que no se puede sacar una url para ese captcha y bajar de ahí la imágen
        # se realiza una captura de pantalla para luego recortarla justo por donde queda el captcha
        location = img_el.location
        size = img_el.size

        self.scrapper.browser.save_screenshot(captcha_filepath) # saves screenshot of entire page
        im = Image.open(captcha_filepath) # uses PIL library to open image in memory

        left = location['x']
        top = location['y']
        right = location['x'] + size['width']
        bottom = location['y'] + size['height']

        im = im.crop((left, top, right, bottom)) # defines crop points
        im.save(captcha_filepath) # saves new cropped image


class DeathByCaptchaResolver(CaptchaResolver):
    def resolve_captcha(self, img_el=None, sol_el=None, captcha_filepath=None, timeout=None):
        def upload_captcha():
            def poll_captcha(captcha_id):
                r = requests.get('http://api.dbcapi.me/api/captcha/%i' % captcha_id, headers={'accept': 'application/json'})
                return simplejson.loads(r.content)

            r = None
            try:
                files = {
                    'username': settings.DEATHBYCAPTCHA_USER,
                    'password': settings.DEATHBYCAPTCHA_PASSWORD,
                    'captchafile': open(captcha_filepath, 'rb')
                }

                # intentamos pedir la resolución del captcha un máximo de MAX_REQ_ATTEMPTS intentos
                num_attempts = 0
                while True:
                    mutex.acquire()
                    try:
                        r = requests.post('http://api.dbcapi.me/api/captcha',
                                          files=files, headers={'Accept': 'application/json'})
                        mutex.release()
                        break
                    except Exception:
                        mutex.release()
                        if num_attempts == MAX_REQ_ATTEMPTS:
                            raise Exception('Max attempts exceeded to send captcha resolution')
                        num_attempts += 1
                        time.sleep(5)

                resp = simplejson.loads(r.content)

                if resp['captcha']:
                    deadline = time.time() + (max(0, timeout) or DEFAULT_TIMEOUT)
                    uploaded_captcha = simplejson.loads(r.content)
                    if uploaded_captcha:
                        while deadline > time.time() and not uploaded_captcha['text']:
                            time.sleep(POLL_INTERVAL)
                            pulled = poll_captcha(uploaded_captcha['captcha'])
                            if pulled['captcha'] == uploaded_captcha['captcha']:
                                uploaded_captcha = pulled
                        if uploaded_captcha['text'] and uploaded_captcha['is_correct']:
                            self.scrapper.captcha_res = uploaded_captcha
            except Exception as ex:
                self.scrapper.logger.exception('Failed uploading CAPTCHA, response:\n\t%s' % r.content)
                self.scrapper.captcha_res = None
                raise ex

            os.remove(captcha_filepath)  # borramos del disco duro la foto que teníamos del captcha

        if type(img_el) is str:
            img_el = self.scrapper.get_css_element(img_el)
        if type(sol_el) is str:
            sol_el = self.scrapper.get_css_element(sol_el)

        # movemos cursor hasta el campo de texto del captcha y hacemos click en él para que la captura salga bien
        self.scrapper.click(sol_el)

        mkdir_if_not_exists(settings.CAPTCHAS_DIR)
        captcha_filepath = captcha_filepath if captcha_filepath else self.scrapper.user.username + '_captcha.png'
        captcha_filepath = os.path.join(settings.CAPTCHAS_DIR, captcha_filepath)
        self.crop_captcha(img_el, captcha_filepath)
        upload_captcha()

        if self.scrapper.captcha_res:
            self.scrapper.fill_input_text(sol_el, self.scrapper.captcha_res['text'].strip())

    def report_wrong_captcha(self):
        try:
            client = deathbycaptcha.SocketClient(settings.DEATHBYCAPTCHA_USER, settings.DEATHBYCAPTCHA_PASSWORD)
            client.report(self.scrapper.captcha_res['captcha'])
            self.scrapper.take_screenshot('wrong_captcha')
            self.scrapper.logger.warning('wrong captcha reported')
        except Exception:
            self.scrapper.logger.error('Failed reporting wrong CAPTCHA')

    # usando la api de esta gente no funciona..

    # def resolve_captcha(self, img_el=None, sol_el=None, captcha_filename=None):
    #     def upload_captcha():
    #         client = deathbycaptcha.SocketClient(settings.DEATHBYCAPTCHA_USER, settings.DEATHBYCAPTCHA_PASSWORD)
    #         try:
    #             # Put your CAPTCHA image file name or file-like object, and optional
    #             # solving timeout (in seconds) here:
    #             self.scrapper.captcha_res = client.decode(captcha_filename)
    #         except Exception:
    #             LOGGER.exception('Failed uploading CAPTCHA')
    #             self.scrapper.captcha_res = None
    #
    #         os.remove(captcha_filename)  # borramos del disco duro la foto que teníamos del captcha
    #
    #     captcha_filename = captcha_filename if captcha_filename else self.scrapper.user.username + '_captcha.png'
    #     self.crop_captcha(img_el, captcha_filename)
    #     upload_captcha()
    #
    #     if self.scrapper.captcha_res:
    #         send_keys(sol_el, self.scrapper.captcha_res['text'])
    #
    # def report_wrong_captcha(self):
    #     try:
    #         client = deathbycaptcha.SocketClient(settings.DEATHBYCAPTCHA_USER, settings.DEATHBYCAPTCHA_PASSWORD)
    #         client.report(self.scrapper.captcha_res['captcha'])
    #     except Exception, e:
    #         LOGGER.exception('Failed reporting wrong CAPTCHA')