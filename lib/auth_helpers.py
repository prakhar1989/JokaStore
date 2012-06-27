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

#helpers for storing encrypted passwords
def make_salt():
    return "".join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    hashed = hashlib.sha256(name + pw + salt).hexdigest()
    return "%s|%s" % (hashed, salt)

def valid_pw(name, pw, h):
    salt = h.split('|')[1]
    return h == make_pw_hash(name, pw, salt)
