from core.models import TwitterBot
from project.models import Tweet
from twitter_bots import settings
import time

__author__ = 'Michel'


from django.core.management.base import BaseCommand, CommandError

settings.set_logger('tweet_sender')


class Command(BaseCommand):
    help = 'Send pending tweets'

    def handle(self, *args, **options):
        settings.LOGGER.info('-- INITIALIZED TWEET SENDER --')
        Tweet.objects.clean_not_sent_ok()

        if args and '1' in args:
            TwitterBot.objects.send_tweet()
        else:
            TwitterBot.objects.send_tweets()

        settings.LOGGER.info('-- FINISHED TWEET SENDER --')

