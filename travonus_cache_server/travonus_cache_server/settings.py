"""
Django settings for travonus_cache_server project.

Generated by 'django-admin startproject' using Django 5.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
# from datetime import timedelta
from dotenv import load_dotenv
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-qj8y3i9@_)6=0nni=2n7il^ig(rvu+9n(bt4z7qx!2n#+vrhaj"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = ["https://travonus-cache-api.ongshak.com"]
# CORS Settings
CORS_ALLOW_ALL_ORIGINS = True
# Update this in production
X_FRAME_OPTIONS = "ALLOWALL"


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps
    "api_handler.apps.ApiHandlerConfig",
    # Celery
    "django_celery_beat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "travonus_cache_server.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "travonus_cache_server.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "travonus_cache",
        "USER": "ongshak",
        "PASSWORD": "123",
        "HOST": "localhost",
        "PORT": "",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Flyhub credentials
FLYHUB_USERNAME = os.getenv("FLYHUB_USERNAME")
FLYHUB_APIKEY = os.getenv("FLYHUB_APIKEY")

# Sabre Credentials
SABRE_TOKEN = os.getenv("SABRE_TOKEN")
SABRE_TOKEN_SANDBOX = os.getenv("SABRE_TOKEN_SANDBOX")
SABRE_USERNAME = os.getenv("SABRE_USERNAME")
SABRE_PASSWORD = os.getenv("SABRE_PASSWORD")
SABRE_PASSWORD_SANDBOX = os.getenv("SABRE_PASSWORD_SANDBOX")
SABRE_PCC = os.getenv("SABRE_PCC")


# Bdfare Credentials
BDFARE_TOKEN = os.getenv("BDFARE_TOKEN")

# proxy credentials
PROXY_SERVER_USERNAME = os.getenv("PROXY_SERVER_USERNAME")
PROXY_SERVER_PASSWORD = os.getenv("PROXY_SERVER_PASSWORD")
PROXY_SERVER_IP = os.getenv("PROXY_SERVER_IP")


# REDIS
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# CELERY WORKER SETUP
CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TIMEZONE = "Asia/Dhaka"


# for uvicorn
ASGI_APPLICATION = "travonous_backend.asgi.application"
