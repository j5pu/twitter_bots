# -*- coding: utf-8 -*-

import time
import twitter_bots.settings as settings
from utils import utc_now


class TwitterEmailNotFound(Exception):
    pass


class TwitterEmailNotConfirmed(Exception):
    def __init__(self, scrapper):
        scrapper.user.twitter_confirmed_email_ok = False
        scrapper.user.save()
        scrapper.logger.warning('Twitter email not confirmed yet')


class TwitterAccountSuspended(Exception):
    def __init__(self, scrapper):
        scrapper.user.mark_as_suspended()
        scrapper.logger.warning('Twitter account suspended')


class TwitterAccountDead(Exception):
    def __init__(self, scrapper):
        scrapper.user.is_dead = True
        scrapper.user.date_death = utc_now()
        scrapper.user.save()
        scrapper.logger.warning('Exceeded 5 attemps to lift suspension. Twitter account dead :(')


class EmailAccountSuspended(Exception):
    def __init__(self, scrapper):
        scrapper.user.is_suspended_email = True
        scrapper.user.save()
        scrapper.logger.warning('Email account suspended')


class BotDetectedAsSpammerException(Exception):
    def __init__(self, scrapper):
        scrapper.user.is_suspended = False
        scrapper.user.save()
        scrapper.logger.warning('Twitter has detected this bot as spammer')


class FailureSendingTweetException(Exception):
    pass


class BotMustVerifyPhone(Exception):
    def __init__(self, scrapper):
        scrapper.user.proxy_for_usage.is_phone_required = True
        scrapper.user.proxy_for_usage.date_phone_required = utc_now()
        scrapper.user.proxy_for_usage.save()
        scrapper.logger.warning('Bot must do mobile phone verification')


class RequestAttemptsExceededException(Exception):
    def __init__(self, scrapper, url):
        scrapper.logger.warning('Exceeded attemps connecting to url %s' % url)


class TwitterBotDontExistsOnTwitterException(Exception):
    def __init__(self, scrapper):
        scrapper.user.mark_as_not_twitter_registered_ok()
        scrapper.logger.warning('Username dont exists on twitter')


class ProxyConnectionError(Exception):
    """Cuando no se puede conectar al proxy"""
    def __init__(self, scrapper):
        scrapper.logger.error('Error connecting to proxy %s' % scrapper.user.proxy_for_usage.__unicode__())
        time.sleep(10)


class InternetConnectionError(Exception):
    """Cuando no se puede conectar al proxy"""
    def __init__(self, scrapper):
        scrapper.logger.error('Error connecting to Internet')
        time.sleep(100)


class ProxyTimeoutError(Exception):
    """Cuando se puede conectar al proxy pero no responde la página que pedimos"""
    def __init__(self, scrapper):

        scrapper.logger.error('Timeout error using proxy %s to request url %s, maybe you are using '
                              'unauthorized IP to connect. Page load timeout: %i secs' %
                              (scrapper.user.proxy_for_usage.__unicode__(),
                               scrapper.browser.current_url, settings.PAGE_LOAD_TIMEOUT))

        scrapper.take_screenshot('proxy_timeout_error', force_take=True)

        if hasattr(scrapper, 'email_scrapper'):
            scrapper.email_scrapper.close_browser()
        else:
            scrapper.close_browser()

        time.sleep(5)


class ProxyUrlRequestError(Exception):
    def __init__(self, scrapper, url):
        scrapper.logger.error('Couldn\'t get url %s behind proxy %s' % (scrapper.user.proxy_for_usage.__unicode__()))
        time.sleep(5)


class ProfileStillNotCompleted(Exception):
    def __init__(self, scrapper):
        scrapper.logger.warning('Profile still not completed')


class IncompatibleUserAgent(Exception):
    def __init__(self, scrapper):
        scrapper.logger.warning('Incompatible user agent')
        scrapper.change_user_agent()


class EmailAccountNotFound(Exception):
    def __init__(self, scrapper):
        scrapper.user.email_registered_ok = False
        scrapper.user.save()
        scrapper.take_screenshot('wrong_email_account')
        scrapper.logger.warning('Wrong email account')
        scrapper.close_browser()
