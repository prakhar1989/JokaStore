import os
import hmac
import random
import string
import hashlib

APP_SECRET_KEY = "itsaseekret"

#helpers for storing encrypted cookies
def hash_str(s):
    return hmac.new(APP_SECRET_KEY, s).hexdigest()

def make_secure_val(s):
    return "%s|%s" % (s, hash_str(s))

def check_secure_val(h):
    val = h.split('|')[0]
    if h == make_secure_val(val):
        return val
