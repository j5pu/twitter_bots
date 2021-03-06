# -*- coding: utf-8 -*-
from selenium.webdriver.common.keys import Keys

from core.scrapper.scrapper import Scrapper
from core.scrapper.captcha_resolvers import DeathByCaptchaResolver
from core.scrapper.exceptions import TwitterEmailNotFound, EmailAccountSuspended, EmailAccountNotFound, \
    HotmailAccountNotCreated, NotInEmailInbox, TwitterAccountSuspended, AboutBlankPage, \
    NotNewTwitterEmailFound, PageNotReadyState, PageNotRetrievedOkByWebdriver, ProxyUrlRequestError, \
    PageLoadError, ConfirmTwEmailError
from core.scrapper.utils import *
from twitter_bots import settings


class HotmailScrapper(Scrapper):

    def sign_up(self):
        def resolve_captcha():
            captcha_resolver.resolve_captcha(
                self.browser.find_elements_by_css_selector('#iHipHolder img')[0],
                self.get_css_element('#iHipHolder input.hipInputText')
            )

        def fix_username(errors=False):
            # username
            if self.check_visibility('#iPwd'):
                self.click('#iPwd')
            if self.check_visibility('#iMembernameLiveError', timeout=5) or \
                    self.check_visibility('#iLiveMessageError'):
                self.take_screenshot('form_wrong_username')
                errors = True
                if self.check_visibility('#sug'):
                    suggestions = self.get_css_elements('#sug #mysugs div a', timeout=10)
                    chosen_suggestion = random.choice(suggestions)
                    self.user.email = chosen_suggestion.text
                    self.click(chosen_suggestion)
                else:
                    self.user.email = generate_random_username(self.user.real_name) + '@hotmail.com'
                    self.fill_input_text('#imembernamelive', self.user.get_email_username())
                    self.delay.seconds(5)
                fix_username(errors)
            else:
                pass

        def submit_form():
            """Comprobamos que todo bien y enviamos registro. Si no sale bien corregimos y volvemos a enviar,
            y así sucesivamente"""

            def check_form():
                errors = False
                self.take_screenshot('checking_form_after_submit')

                self.delay.seconds(7)  # todo: comprobar después de captcha
                fix_username(errors)

                # error en passwords
                if self.check_visibility('#iPwdError'):
                    errors = True
                    self.user.password_email = generate_random_string()
                    self.fill_input_text('#iPwd', self.user.password_email)
                    self.fill_input_text('#iRetypePwd', self.user.password_email)

                # error en captcha
                captcha_errors = self.get_css_elements('.hipErrorText')
                captcha_error_visible = captcha_errors and \
                                        (
                                            self.check_visibility(captcha_errors[1], timeout=5) or
                                            self.check_visibility(captcha_errors[2], timeout=5)
                                        )
                if captcha_error_visible:
                    self.click('#iHipHolder input.hipInputText')
                    self.take_screenshot('form_wrong_captcha', force_take=True)
                    errors = True
                    #captcha_resolver.report_wrong_captcha()
                    resolve_captcha()

                return errors

            self.click('#createbuttons input')

            errors = check_form()
            if errors:
                submit_form()

        def fill_form():
            self.click('#iliveswitch')
            self.fill_input_text('#iFirstName', self.user.real_name.split(' ')[0])
            self.fill_input_text('#iLastName', self.user.real_name.split(' ')[1])

            # cambiamos de @outlok a hotmail
            self.click('#idomain')
            self.send_special_key(Keys.ARROW_DOWN)
            self.send_special_key(Keys.ENTER)

            # username (lo que va antes del @)
            self.fill_input_text('#imembernamelive', self.user.get_email_username())

            # provocamos click en pwd para que salte lo de apañar el nombre de usuario
            fix_username()

            # una vez corregido el nombre de usuario seguimos rellenando el password y demás..
            self.fill_input_text('#iPwd', self.user.password_email)
            self.fill_input_text('#iRetypePwd', self.user.password_email)
            self.fill_input_text('#iZipCode', self.get_usa_zip_code())

            # FECHA DE NACIMIENTO
            self.click('#iBirthMonth')
            for _ in range(0, self.user.birth_date.month):
                self.send_special_key(Keys.ARROW_DOWN)
            self.delay.seconds(1)
            self.fill_input_text('#iBirthDay', self.user.birth_date.day)
            self.delay.seconds(1)
            self.fill_input_text('#iBirthYear', self.user.birth_date.year)

            # SEXO
            self.click('#iGender')
            for _ in range(0, self.user.gender+1):
                self.send_special_key(Keys.ARROW_DOWN)

            self.fill_input_text('#iAltEmail', generate_random_username() + '@gmail.com')

            resolve_captcha()

            self.click('#iOptinEmail')

        self.logger.info('Signing up %s..' % self.user.email)
        self.go_to(settings.URLS['hotmail_reg'])
        captcha_resolver = DeathByCaptchaResolver(self)
        self.wait_visibility_of_css_element('#iliveswitch', timeout=10)
        fill_form()
        self.delay.seconds(5)
        submit_form()
        try:
            wait_condition(lambda: 'Microsoft account | Home'.lower() in self.browser.title.lower())
        except Exception:
            raise HotmailAccountNotCreated(self)

    def check_account_suspended(self):
        suspended = lambda: 'unblock' in self.browser.title.lower() or \
                            'overprotective' in self.browser.title.lower()
        suspended = check_condition(suspended)
        if suspended and self.check_invisibility('#skipLink'):
            raise EmailAccountSuspended(self)

    def login(self):
        def submit_form(attempts=0):
            def check_form():
                errors = False

                if self.check_visibility('#idTd_Tile_ErrorMsg_Login', timeout=10):
                    errors = True

                    if self.check_visibility('#idTd_HIP_HIPControl'):
                        # si hay captcha que rellenar..
                        cr = DeathByCaptchaResolver(self)
                        cr.resolve_captcha('#idTd_HIP_HIPControl img', '#idTd_HIP_HIPControl input')
                        self.fill_input_text('input[name=passwd]', self.user.password_email)
                    else:
                        # si no hay captcha entonces lanzamos excepción diciendo que el email no existe como registrado
                        raise EmailAccountNotFound(self)
                return errors

            if attempts > 1:
                # self.user.email_registered_ok = False
                # self.user.save()
                self.take_screenshot('too_many_attempts')
                self.close_browser()
                raise Exception('too many attempts to login %s' % self.user.email)

            self.click('input[type="submit"]')
            errors = check_form()
            if errors:
                submit_form(attempts+1)

        try:
            self.go_to(settings.URLS['hotmail_login'])
            self.wait_to_page_readystate()
            self.delay.seconds(5)
            if self.check_visibility('#idDiv_PWD_UsernameTb'):
                self.fill_input_text('#idDiv_PWD_UsernameTb input', self.user.email)
                self.fill_input_text('#idDiv_PWD_PasswordTb input', self.user.password_email)
                self.click('#idChkBx_PWD_KMSI0Pwd')  # para mantener la sesión si cierro navegador
                submit_form()
                self.wait_to_page_readystate()

            # a partir de aquí se supone que no debería aparecer más en la página de sign in
            if 'sign in' in self.browser.title.lower():
                raise PageNotRetrievedOkByWebdriver(self)
            else:
                self.delay.seconds(10)
                self.wait_to_page_readystate()
                self.clear_local_storage()
                self._quit_inbox_shit()
                self.check_account_suspended()
                self.logger.debug('Logged in hotmail ok')

                # por si no se había marcado en BD
                if not self.user.email_registered_ok:
                    self.user.email_registered_ok = True
                    self.user.save()
        except (EmailAccountNotFound,
                EmailAccountSuspended,
                PageLoadError) as e:
            raise e
        except Exception as e:
            self.logger.exception('Error on hotmail login')
            raise e

    def _quit_inbox_shit(self):
        # en el caso de aparecer esto tras el login le damos al enlace que aparece en la página
        if check_condition(lambda: 'BrowserSupport' in self.browser.current_url):
            self.take_screenshot('continue_to_your_inbox_link')
            self.click(self.browser.find_element_by_partial_link_text('continue to your inbox'))

        self.wait_to_page_readystate()

        self.try_to_click('#notificationContainer button', timeout=10)

    def confirm_tw_email(self):
        def skip_confirmation_shit():
            while True:
                if self.check_visibility('#idDiv_PWD_PasswordExample'):
                    self.fill_input_text('#idDiv_PWD_PasswordExample', self.user.password_email)
                    self.click('#idSIButton9')
                    self.wait_to_page_readystate()
                    self.try_to_click('#idBtn_SAOTCS_Cancel', 'a#iShowSkip')
                    self.wait_to_page_readystate()
                elif self.check_visibility('#idBtn_SAOTCS_Cancel'):
                    self.click('#idBtn_SAOTCS_Cancel')
                    self.wait_to_page_readystate()
                elif self.check_visibility('a#iShowSkip'):
                    self.click('a#iShowSkip')
                    self.wait_to_page_readystate()
                else:
                    self.wait_to_page_readystate()
                    self.take_screenshot('confirmation_shit_skipped')
                    break

        def get_email_title_on_inbox():
            return get_element(lambda: self.browser.find_element_by_partial_link_text('Confirm your'))

        def on_inbox_page():
            return self.check_visibility('div.c-MessageGroup')

        def click_on_inbox_msg():
            self.logger.debug('still on inbox, reclicking confirm email title..')
            self.click(get_email_title_on_inbox())
            # si no se ha clickeado bien y aparece el menu de notif
            if self.check_visibility('#notificationContainer div'):
                self.click('#notificationContainer')
                self.click(get_email_title_on_inbox())
            self.wait_to_page_readystate()

        def check_if_still_on_inbox():
            while on_inbox_page():
                click_on_inbox_msg()
                self.wait_to_page_readystate()
                self.delay.seconds(4)

        try:
            self.logger.info('Confirming twitter email %s..' % self.user.email)
            self.login()

            # vemos si realmente estamos en la bandeja de entrada
            # if not self.check_visibility('#pageInbox'):
            #     self.take_screenshot('not_really_on_inbox_page', force_take=True)
            #     raise Exception('%s is not really on inbox page after login' % self.user.email)
            # else:
            skip_confirmation_shit()
            self._quit_inbox_shit()
            self.take_screenshot('on_inbox_page')

            skip_confirmation_shit()
            self.try_to_click('#skipLink')

            inbox_msgs_css = '.InboxTable ul.InboxTableBody li'
            emails = self.get_css_elements(inbox_msgs_css)
            if not emails:
                skip_confirmation_shit()
                emails = self.get_css_elements(inbox_msgs_css)

            if emails:
                if len(emails) < 2:
                    self.logger.warning('No twitter email arrived, resending twitter email..')
                    raise TwitterEmailNotFound(self)
                else:
                    #twitter_email_title = get_element(lambda: self.browser.find_element_by_partial_link_text('Confirm'))
                    self.delay.seconds(10)
                    skip_confirmation_shit()

                    # sólo clickeamos si el mensaje más reciente no fue leído
                    emails = self.get_css_elements(inbox_msgs_css)
                    was_read = 'mlUnrd' not in emails[0].get_attribute('class')
                    if was_read:
                        raise NotNewTwitterEmailFound(self)
                    else:
                        twitter_email_title = get_email_title_on_inbox()

                        self.click(twitter_email_title)
                        check_if_still_on_inbox()

                        self.delay.seconds(2)

                        # si sale confirm otra vez y se vuelve a ir a la inbox..
                        skip_confirmation_shit()
                        check_if_still_on_inbox()

                        self.delay.seconds(4)
                        confirm_btn = get_element(lambda: self.browser.find_element_by_partial_link_text('Confirm now'))
                        if confirm_btn:
                            self.click(confirm_btn)
                        else:
                            self.try_to_click('.ecxbutton_link', '.ecxmedia_main > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(4) > td:nth-child(1) > a:nth-child(2)')

                        self.delay.seconds(3)
                        self.switch_to_window(-1)
                        self.wait_to_page_readystate()
                        self.delay.seconds(3)

                        # si aparece como suspendido lo tratamos más adelante
                        if 'suspended' in self.browser.title.lower():
                            raise TwitterAccountSuspended(self.user)

                        # si no cargó bien la página de twitter de pulsar el enlace, aunque confirme igualmente,
                        # lo anotamos en el log
                        elif 'about:blank' in self.browser.current_url:
                            self.logger.warning('about:blank on twitter page after clicking confirmation link')
                            # raise AboutBlankPage(self)

                        # si ha ido ok pero nos pide meter usuario y contraseña
                        elif not self.check_visibility('#global-new-tweet-button'):
                            self.send_keys(self.user.username)
                            self.send_special_key(Keys.TAB)
                            self.send_keys(self.user.password_twitter)
                            self.send_special_key(Keys.ENTER)
                            self.delay.seconds(7)
            else:
                raise NotInEmailInbox(self)
        except (TwitterEmailNotFound,
                TwitterAccountSuspended,
                PageLoadError,
                NotNewTwitterEmailFound,
                NotInEmailInbox):
            raise ConfirmTwEmailError
