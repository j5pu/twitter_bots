from twitter_bots import settings

__author__ = 'Michel'


class RateLimitedException(Exception):
    def __init__(self):
        settings.LOGGER.warning('Rate limit exceeded getting from twitter API')