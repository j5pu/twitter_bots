# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Extractor'
        db.create_table(u'project_extractor', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('consumer_key', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('consumer_secret', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('access_token', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('access_token_secret', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal(u'project', ['Extractor'])


    def backwards(self, orm):
        # Deleting model 'Extractor'
        db.delete_table(u'project_extractor')


    models = {
        u'core.twitterbot': {
            'Meta': {'object_name': 'TwitterBot'},
            'birth_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'cookies': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_suspended_email': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_suspended_twitter': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'email_registered_ok': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'gender': ('django.db.models.fields.IntegerField', [], {'default': '0', 'max_length': '1'}),
            'has_fast_mode': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_manually_registered': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'it_works': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_verify_phone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password_email': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'password_twitter': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'proxy': ('django.db.models.fields.CharField', [], {'max_length': '21', 'blank': 'True'}),
            'proxy_provider': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'random_mouse_paths': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'random_offsets': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'real_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'twitter_avatar_completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'twitter_bio_completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'twitter_confirmed_email_ok': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'twitter_registered_ok': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user_agent': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'webdriver': ('django.db.models.fields.CharField', [], {'default': "'FI'", 'max_length': '2'})
        },
        u'project.extractor': {
            'Meta': {'object_name': 'Extractor'},
            'access_token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'access_token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'consumer_key': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'consumer_secret': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'project.follower': {
            'Meta': {'object_name': 'Follower'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'target_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'followers'", 'to': u"orm['project.TargetUser']"}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'follower'", 'to': u"orm['project.TwitterUser']"})
        },
        u'project.link': {
            'Meta': {'object_name': 'Link'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'platform': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'links'", 'to': u"orm['project.Project']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'project.project': {
            'Meta': {'object_name': 'Project'},
            'has_tracked_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'target_users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'projects'", 'blank': 'True', 'to': u"orm['project.TargetUser']"})
        },
        u'project.targetuser': {
            'Meta': {'object_name': 'TargetUser'},
            'followers_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'next_cursor': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'null': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        u'project.tweet': {
            'Meta': {'object_name': 'Tweet'},
            'bot_used': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tweets'", 'null': 'True', 'to': u"orm['core.TwitterBot']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'tweet'", 'null': 'True', 'to': u"orm['project.Link']"}),
            'mentioned_users': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'mentions'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['project.TwitterUser']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tweets'", 'to': u"orm['project.Project']"}),
            'sending': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sent_ok': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'tweet_msg': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['project.TweetMsg']"})
        },
        u'project.tweetmsg': {
            'Meta': {'object_name': 'TweetMsg'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tweet_msgs'", 'to': u"orm['project.Project']"}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '101'})
        },
        u'project.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {}),
            'followers_count': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'full_name': ('django.db.models.fields.CharField', [], {'max_length': '160', 'null': 'True'}),
            'geo_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'en'", 'max_length': '2'}),
            'last_tweet_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'source': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'time_zone': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True'}),
            'tweets_count': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '160'}),
            'verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['project']