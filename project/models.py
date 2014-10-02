import datetime
from django.db import models
from django.db.models import Count
import simplejson
import tweepy
from core.models import TwitterBot
from project.exceptions import RateLimitedException
from project.managers import TargetUserManager, TweetManager, ProjectManager
from twitter_bots import settings


class Project(models.Model):
    name = models.CharField(max_length=100, null=False, blank=True)
    target_users = models.ManyToManyField('TargetUser', related_name='projects', blank=True)
    is_running = models.BooleanField(default=True)
    has_tracked_clicks = models.BooleanField(default=False)

    objects = ProjectManager()

    def __unicode__(self):
        return self.name

    # GETTERS

    def get_tweets_pending_to_send(self):
        return Tweet.objects.filter(project=self, sent_ok=False, sending=False)

    def get_followers(self, platform=None):
        total_followers = Follower.objects.filter(target_user__projects=self)
        if platform:
            return total_followers.filter(twitter_user__source=platform)
        else:
            return total_followers

    def get_followers_count(self):
        return self.get_followers().count()

    def get_followers_to_mention(self, platform=None):
        project_followers = self.get_followers(platform=platform)
        project_followers = project_followers.annotate(mentions_count=Count('twitter_user__mentions'))
        return project_followers.filter(mentions_count=0)

    def has_all_mentioned(self):
        pass
        # return self.filter(target_users__followers)

    def get_platforms(self, only_select=None):
        "Only select indicara las plataformas que queremos obtener entre las disponibles para el proyecto"
        platforms = Link.objects.filter(project=self).values('platform').distinct()
        return [pl['platform'] for pl in platforms]


class TweetMsg(models.Model):
    text = models.CharField(max_length=101, null=False, blank=False)
    project = models.ForeignKey(Project, related_name='tweet_msgs')

    def __unicode__(self):
        return '%s @ %s' % (self.text, self.project.name)


class TargetUser(models.Model):
    username = models.CharField(max_length=80, null=False, blank=True)
    # cuando el cursor sea null es que se han extraido todos sus followers
    next_cursor = models.BigIntegerField(null=True, default=0)
    followers_count = models.PositiveIntegerField(null=True, default=0)

    objects = TargetUserManager()

    def __unicode__(self):
        return self.username

    def followers_saved(self):
        return Follower.objects.filter(target_user=self).count()

    def followers_android(self):
        return Follower.objects.filter(target_user=self, twitter_user__source=TwitterUser.ANDROID).count()


class Follower(models.Model):
    target_user = models.ForeignKey(TargetUser, related_name='followers', null=False)
    twitter_user = models.ForeignKey('TwitterUser', related_name='follower', null=False)

    def __unicode__(self):
        return '%s -> %s' % (self.twitter_user, self.target_user)

    def was_mentioned(self, project=None):
        """Mira si el follower aparece mencionado para todos los proyectos o el dado por parametro"""
        tweets = Tweet.objects.filter(mentioned_users__follower=self)
        if project:
            tweets = tweets.filter(project=project)
        if tweets:
            return True
        else:
            return False


class TwitterUser(models.Model):
    DEFAULT_LANG = 'en'
    OTHERS = 0
    IOS = 1
    IPAD = 2
    IPHONE = 3
    ANDROID = 4
    SOURCES = (
        (OTHERS, 'others'),
        (IOS, 'ios'),
        (IPAD, 'ipad'),
        (IPHONE, 'iphone'),
        (ANDROID, 'android'),
    )
    source = models.PositiveIntegerField(null=False, choices=SOURCES, default=0)
    username = models.CharField(max_length=160, null=False)
    full_name = models.CharField(max_length=160, null=True)
    twitter_id = models.BigIntegerField(null=False)

    # GEO
    geo_enabled = models.BooleanField(default=False)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    city = models.CharField(max_length=80, null=True)
    country = models.CharField(max_length=2, null=True)

    # TIME
    created_date = models.DateTimeField(null=False)
    time_zone = models.CharField(max_length=50, null=True)  # te da la zona horaria por la ciudad, x. ej 'Madrid'
    last_tweet_date = models.DateTimeField(null=True)

    language = models.CharField(max_length=2, null=False, default=DEFAULT_LANG)
    followers_count = models.PositiveIntegerField(null=True)
    tweets_count = models.PositiveIntegerField(null=True)
    verified = models.BooleanField(default=False)

    def __unicode__(self):
        return self.username


class Tweet(models.Model):
    tweet_msg = models.ForeignKey(TweetMsg, null=False)
    link = models.ForeignKey('Link', null=True, blank=True, related_name='tweet')
    date_created = models.DateTimeField(auto_now_add=True)
    date_sent = models.DateTimeField(null=True, blank=True)
    project = models.ForeignKey(Project, related_name="tweets")
    mentioned_users = models.ManyToManyField(TwitterUser, related_name='mentions', null=True, blank=True)
    sending = models.BooleanField(default=False)
    sent_ok = models.BooleanField(default=False)
    bot_used = models.ForeignKey(TwitterBot, related_name='tweets', null=True)

    objects = TweetManager()

    def __unicode__(self):
        return self.compose()

    def compose(self):
        mu_txt = ''
        for mu in self.mentioned_users.all():
            mu_txt += '@%s ' % mu.username

        link_txt = ' ' + self.link.url if self.link else ''

        return mu_txt + self.tweet_msg.text + link_txt

    def length(self):
        def mentioned_users_space():
            length = 0
            for mu in self.mentioned_users.all():
                length += len(mu.username) + 2
            return length

        total_lenght = 0
        total_lenght += mentioned_users_space()
        total_lenght += len(self.tweet_msg.text)
        if self.link:
            total_lenght += 1 + len(self.link.url)
        return total_lenght

    def has_space(self):
        """Devuelve si el tweet no supera los 140 caracteres"""
        return self.length() < 140

    def exceeded_tweet_limit(self):
        return self.length() > 140

    def is_available(self):
        return not self.sending and not self.sent_ok


class Link(models.Model):
    url = models.URLField(null=False)
    project = models.ForeignKey(Project, null=False, related_name='links')
    platform = models.IntegerField(null=False, choices=TwitterUser.SOURCES, default=0)

    def __unicode__(self):
        return '%s @ %s' % (self.project.name, self.get_platform_display())


class Extractor(models.Model):
    #     consumer_key = "ESjshGwY13JIl3SLF4dLiQVDB"
    #     consumer_secret = "QFD2w79cXOXoGOf1TDbcSxPEhVJWtjGhMHrFTkTiouwreg9nJ3"
    #     access_token = "2532144721-eto2YywaV7KF0gmrHLhYSWiZ8X22xt8KuTItV83"
    #     access_token_secret = "R6zdO3qVsLP0RuyTN25nCqfxvtCyUydOVzFn8NCzJezuG"
    BASE_URL = 'https://api.twitter.com/1.1/'

    consumer_key = models.CharField(null=False, max_length=200)
    consumer_secret = models.CharField(null=False, max_length=200)
    access_token = models.CharField(null=False, max_length=200)
    access_token_secret = models.CharField(null=False, max_length=200)
    twitter_bot = models.OneToOneField(TwitterBot, null=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.twitter_bot.username

    def connect_twitter_api(self):
        # self.api = req.OAuth1Session(self.consumer_key,
        #                              client_secret=self.consumer_secret,
        #                              resource_owner_key=self.access_token,
        #                              resource_owner_secret=self.access_token_secret,
        #                              proxies={'https': self.twitter_bot.proxy})
        auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_token_secret)
        self.api = tweepy.API(auth)

    def get(self, uri):
        # url = 'https://api.twitter.com/1.1/followers/list.json?cursor=2&screen_name=candycrush&count=5000'
        resp = self.api.get(self.BASE_URL + uri)
        return simplejson.loads(resp.content)

    def get_user_info(self, username):
        return self.get('users/show.json?screen_name=%s' % username)

    # def format_datetime(self, twitter_datetime_str):
    #     if not twitter_datetime_str:
    #         return None
    #     else:
    #         return datetime.datetime.strptime(twitter_datetime_str, '%a %b %d %H:%M:%S +0000 %Y')

    def format_source(self, user_source_str):
        low = user_source_str.lower()
        if 'iphone' in low:
            return TwitterUser.IPHONE
        elif 'ipad' in low:
            return TwitterUser.IPAD
        elif 'ios' in low:
            return TwitterUser.IOS
        elif 'android' in low:
            return TwitterUser.ANDROID
        else:
            return TwitterUser.OTHERS

    def update_target_user_data(self, target_user):
        tw_user = self.api.get_user(screen_name=target_user.username)
        target_user.followers_count = tw_user.followers_count
        target_user.save()

    def extract_followers(self, target_username):

        def create_twitter_user(tw_follower):
            twitter_user = TwitterUser.objects.filter(twitter_id=tw_follower.id)
            if not twitter_user.exists():
                twitter_user = TwitterUser()
                settings.LOGGER.info('Creating new twitter user %s' % tw_follower.screen_name)
            else:
                if len(twitter_user) > 1:
                    raise Exception('Duplicated twitter user with id %i' % twitter_user[0].twitter_id)
                else:
                    twitter_user = twitter_user[0]
                    settings.LOGGER.info('Twitter user %s exists previously saved. Getting..' % twitter_user.username)

            twitter_user.twitter_id = tw_follower.id
            twitter_user.created_date = tw_follower.created_at
            twitter_user.followers_count = tw_follower.followers_count
            twitter_user.geo_enabled = tw_follower.geo_enabled
            twitter_user.language = tw_follower.lang[:2] if tw_follower.lang else TwitterUser.DEFAULT_LANG
            twitter_user.full_name = tw_follower.name
            twitter_user.username = tw_follower.screen_name
            twitter_user.tweets_count = tw_follower.statuses_count
            twitter_user.time_zone = tw_follower.time_zone
            twitter_user.verified = tw_follower.verified

            if 'status' in tw_follower:
                if 'created_at' in tw_follower.status:
                    twitter_user.last_tweet_date = self.format_datetime(tw_follower.status.created_at)
                if 'source' in tw_follower.status:
                    twitter_user.source = self.format_source(tw_follower['status']['source'])
                else:
                    twitter_user.source = TwitterUser.OTHERS
            else:
                twitter_user.source = TwitterUser.OTHERS

            twitter_user.save()
            settings.LOGGER.info('Twitter user %s saved ok' % twitter_user.username)
            return twitter_user

        self.connect_twitter_api()

        target_user = TargetUser.objects.get_or_create(username=target_username)[0]
        self.update_target_user_data(target_user)

        next_cursor = target_user.next_cursor
        while True:
            settings.LOGGER.info('Extractor %s retrieving %s followers (cursor %i)' % (self.twitter_bot.username, target_username, next_cursor))

            kwargs = {
                'screen_name': target_username,
                'count': 200
            }

            # si esta a None entonces se dan por procesados todos sus followers
            if next_cursor == None:
                break
            elif next_cursor != 0:
                kwargs.update({'cursor': next_cursor})

            try:
                tw_followers = self.api.followers(kwargs)
            except tweepy.error.TweepError as ex:
                if ex.response.status == 429:
                    raise RateLimitedException(self)

            for tw_follower in tw_followers:
                # creamos twitter_user a partir del follower si ya no existe en BD
                twitter_user = create_twitter_user(tw_follower)
                Follower.objects.get_or_create(twitter_user=twitter_user, target_user=target_user)

            # actualizamos el next_cursor para el target user
            next_cursor = resp['next_cursor']
            if not next_cursor:
                next_cursor = None
                target_user.next_cursor = next_cursor
                target_user.save()
                settings.LOGGER.info('All followers from %s retrieved ok' % target_username)
                break
            else:
                target_user.next_cursor = next_cursor
                target_user.save()