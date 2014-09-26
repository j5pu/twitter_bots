from twitter_bots import settings
from django.db import models


class TargetUserManager(models.Manager):
    def create(self, **kwargs):
        target_user_created = super(TargetUserManager, self).create(**kwargs)
        target_user_created.process()


class TweetManager(models.Manager):
    def get_pending(self):
        return self.filter(sending=False, sent_ok=False)
        settings.LOGGER.info('Pending tweets to send retrieved')

    def get_sent_ok(self):
        return self.filter(sent_ok=True)

    def all_sent_ok(self):
        return self.get_sent_ok().count() == self.all().count()

    def clean_pending(self):
        "Vuelve a marcar como disponible para que lo envie algun robot"
        self.filter(sending=True).update(sending=False, bot_used=None)
        settings.LOGGER.info('Cleaned pending tweets to send')
