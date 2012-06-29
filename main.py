import os
import sys
import webapp2
import json
import jinja2
import datetime
import logging
from google.appengine.ext import db
from google.appengine.api import memcache

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

### BASE HANDLER CLASS ###
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = auth_helpers.make_secure_val(val)
        self.response.headers.add_header(
                'Set-Cookie', "%s=%s; Path=/" % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and auth_helpers.check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

def users_key(group = "default"):
    return db.Key.from_path('users', group)

### AUTH STUFF ###
class User(db.Model):
    username = db.StringProperty(required = True)
    email = db.StringProperty()
    pw_hash = db.StringProperty(required = True)

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('username =', name).get()
        return u

    @classmethod
    def register(cls, name, pw, email=None):
        pw_hash = auth_helpers.make_pw_hash(name, pw)
        return User(parent = users_key(),
                    username = name,
                    pw_hash = pw_hash,
                    email = email)
    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and auth_helpers.valid_pw(name, pw, u.pw_hash):
            return u

def get_tshirts(update = False):
    key = "tee"
    tshirts = memcache.get(key)
    if tshirts is None or update:
        logging.error("DB QUERY FOR TSHIRTS")
        tshirts = db.GqlQuery("SELECT * FROM Tshirt ORDER BY tshirt_id")
        tshirts = list(tshirts)
        memcache.set(key, tshirts)
    return tshirts

def get_one_tshirt(item_id, update = False):
    key = item_id 
    tshirt = memcache.get(key)
    if tshirt is None or update:
        logging.error("DB QUERY FOR SINGLE TSHIRT")
        tshirt = Tshirt.all().filter("tshirt_id =", int(item_id)).get()
        memcache.set(key, tshirt)
    return tshirt

class Tshirt(db.Model):
    tshirt_id = db.IntegerProperty(required = True)
    title = db.StringProperty(required = True)
    price = db.IntegerProperty()
    content = db.TextProperty()
    votes =  db.IntegerProperty()

class MainPage(Handler):
    def get(self):
        tshirts = get_tshirts()
        self.render("main.html", tshirts = tshirts)


class AddItemHandler(Handler):
    def get(self):
        self.render("items_form.html")

    def post(self):
        self.item_id = self.request.get('item_id')
        self.item_title = self.request.get('title')
        self.item_price = self.request.get('price')
        self.item_content = self.request.get('content')
        
        t = Tshirt(tshirt_id = int(self.item_id), 
                   title = self.item_title, 
                   price = int(self.item_price), 
                   content = self.item_content)
        t.put()
        self.redirect('/item/add')

class EditItemHandler(Handler):
    def get(self):
        db.query("DB QUERY FOR SINGLE TSHIRT")
        tshirts = db.GqlQuery("SELECT * FROM Tshirt ORDER BY tshirt_id")
        self.render("items_form.html", tshirts = tshirts)

    def post(self):
        self.item_id = self.request.get('item_id')
        self.item_title = self.request.get('title')
        self.item_price = self.request.get('price')
        self.item_content = self.request.get('content')

        tshirt = Tshirt.all().filter("tshirt_id =", int(self.item_id)).get()
        tshirt.title = self.item_title
        tshirt.content = self.item_content
        tshirt.price = int(self.item_price)

        tshirt.put()
        self.redirect('/item/edit')

class ShowItemHandler(Handler):
    def get(self, item_id):
        tshirt = get_one_tshirt(item_id)
        self.render("show_tshirt.html", tshirt = tshirt)

class AboutHandler(Handler):
    def get(self):
        pass

class HelpHandler(Handler):
    def get(self):
        pass

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/item/add', AddItemHandler), 
                               ('/item/edit', EditItemHandler), 
                               ('/about', AboutHandler),
                               ('/help', HelpHandler),
                               ('/tshirt/(\d+)', ShowItemHandler)], debug=True)
