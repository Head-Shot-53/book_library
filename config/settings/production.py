from .base import *
from .base import env

DEBUG = False


ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])


SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"
