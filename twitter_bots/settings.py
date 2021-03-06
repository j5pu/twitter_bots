# -*- coding: utf-8 -*-

from __future__ import absolute_import
# ^^^ The above is required if you want to import from the celery
# library.  If you don't have this then `from celery.schedules import`
# becomes `proj.celery.schedules` in Python 2.x since it allows
# for relative imports by default.

# Celery settings
import socket

BROKER_URL = 'amqp://robots:1aragon1@localhost/robots'
CELERY_RESULT_BACKEND = 'amqp'
# BROKER_URL = 'redis://localhost:6379/0'
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
# CELERY_AMQP_TASK_RESULT_EXPIRES = 60*30
# BROKER_POOL_LIMIT = 100

#: Only add pickle to this list if your broker is secured
#: from unwanted access (see userguide/security.html)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'


import logging

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'b%wzymfw7a-)uhmz!^5er^5e^&ko&ym=@7ugjhtaik+3p7=olz'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

PROD_MODE = False

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # packages
    'south',

    # apps
    'core',
    'project',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'twitter_bots.urls'

WSGI_APPLICATION = 'twitter_bots.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",

        "NAME": "twitter_bots_spare_time",
        "USER": "root",
        "PASSWORD": "1aragon1",
        "HOST": "127.0.0.1",
        # "HOST": "88.26.212.82",
        "PORT": "3306",

        # "NAME": "twitter_bots_dev",
        # "USER": "root",
        # "PASSWORD": "1aragon1",
        # # "HOST": "192.168.1.115",
        # "HOST": "88.26.212.82",
        # "PORT": "3306",
    },
}


# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

AUTH_USER_MODEL = "core.User"


LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
# logger


class IgnoreErrorsFilter(logging.Filter):
    def filter(self, record):
        return record.levelname != 'ERROR' and record.levelname != 'CRITICAL' and record.levelname != 'EXCEPTION'


class HostnameFormatter(logging.Formatter):
    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        record.__dict__['hostname'] = socket.gethostname()

        s = self._fmt % record.__dict__
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            try:
                s = s + record.exc_text
            except UnicodeError:
                # Sometimes filenames have non-ASCII chars, which can lead
                # to errors when s is Unicode and record.exc_text is str
                # See issue 8924.
                # We also use replace for when there are multiple
                # encodings, e.g. UTF-8 for the filesystem and latin-1
                # for a script. See issue 13232.
                s = s + record.exc_text.decode(sys.getfilesystemencoding(),
                                               'replace')
        return s


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            '()': HostnameFormatter,
            # 'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            'format': "[%(asctime)s] %(module)s:%(lineno)d\t %(levelname)s\t\t%(threadName)s@%(hostname)s - %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'ignore_errors': {
            '()': IgnoreErrorsFilter
        },
        'slow_queries': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: record.duration > 0.05 # output slow queries only
        },
    },
    'handlers': {
        'console_info': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'stream': sys.stdout,
            'filters': ['ignore_errors'],
        },
        'console_error': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'management_logs_file_debug': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/{log_filename}.debug.log'),
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'verbose',
        },
        'management_logs_file_info': {
            'level':'INFO',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/{log_filename}.info.log'),
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'verbose',
        },
        'db_log_slow': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/db_slow_queries.log'),
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'verbose',
            'filters': ['slow_queries'],
        },
        'db_log': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/db.log'),
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'verbose',
        }
    },
    'loggers': {
        'project.management.commands': {
            'handlers': [
                'console_info',
                'console_error',
                'management_logs_file_info',
                'management_logs_file_debug'
            ],
            'level': 'DEBUG',
            'propagate': True,
        },
        'project.management.commands.mention_processor': {
            'handlers': [
                'management_logs_file_info',
                'management_logs_file_debug'
            ],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.tasks': {
            'handlers': [
                'management_logs_file_info',
                'management_logs_file_debug'
            ],
            'level': 'DEBUG',
            'propagate': False,
        },
        'default': {
            'handlers': ['console_info', 'console_error'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.db': {
            'handlers': ['db_log'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

LOGGER = None


from core.scrapper.settings import *


def set_logger(name):
    # import copy
    # custom_logger = copy.deepcopy(LOGGING)
    global LOGGING, LOGGER
    for handler in LOGGING['handlers'].values():
        if handler['class'] == 'logging.FileHandler' or handler['class'] == 'logging.handlers.RotatingFileHandler':
            handler['filename'] = handler['filename'].format(log_filename=name.split('.')[-1])

    import logging
    import logging.config
    logging.config.dictConfig(LOGGING)
    LOGGER = logging.getLogger(name)


SUPERVISOR_LOGS_DIR = os.path.join(LOGS_DIR, 'supervisor')

SPANISH = 'es'
ENGLISH = 'en'
LANGUAGES = {
    (SPANISH, 'Spanish'),
    (ENGLISH, 'English'),
}


