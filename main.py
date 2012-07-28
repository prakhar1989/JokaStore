import os
import sys
import webapp2
import json
import jinja2
import datetime
import logging
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users
from webapp2_extras import sessions
from google.appengine.api import mail

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)
### Configuration ###
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'my-super-secret-key',
}

### BASE HANDLER CLASS ###
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, 
                    logged_in = users.get_current_user(),
                    item_count = self.session.get('item_count'),**kw))

    def dispatch(self):
        self.session_store = sessions.get_store(request=self.request)
        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        return self.session_store.get_session()

    def get_items_from_cart(self):
        """ Fetches items from sessions cart"""
        item_list = []
        cart_count = self.session.get('add_to_cart_count')
        if not cart_count: return None;
        for i in range(1, cart_count+1):
            item = self.session.get(str(i))
            if item:
                item_list.append(item)
        return item_list

### MODELS ###
class Tshirt(db.Model):
    tshirt_id = db.IntegerProperty(required = True)
    title = db.StringProperty(required = True)
    price = db.IntegerProperty()
    content = db.TextProperty()

class Order(db.Model):
    qty = db.IntegerProperty(required = True)
    size = db.StringProperty(required = True)
    tshirt_id = db.IntegerProperty(required = True)
    user_email = db.StringProperty(required = True)
    time_of_order = db.DateTimeProperty(auto_now_add = True)

### CACHING ###
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

### CONTROLLERS ###
class MainPage(Handler):
    """ This is the main page which uses server-side templating
    to display all items. Use this in emergency by changing routing 
    mappings. Currently mapped to /mainpage"""
    def get(self):
        tshirts = get_tshirts(update = True)
        self.render("main.html", tshirts = tshirts)

class AnotherMainPage(Handler):
    """ This is the main page which uses client-side handlebars 
    for templating. Currently mapped to /"""
    def get(self):
        self.render("main2.html")

class JSONHandler(Handler):
    def get(self):
        tshirts = get_tshirts(True)
        self.response.headers['Content-type'] = 'application/json'
        tshirt_json = []
        for t in tshirts:
            tshirt_json.append({"id": t.tshirt_id, "title": t.title})
        self.write(json.dumps(tshirt_json))

class LoginHandler(Handler):
    def get(self):
        user = users.get_current_user()
        if user:
            self.session["item_count"] = 0
            self.session["add_to_cart_count"] = 0
            self.redirect('/')
        else:
            self.redirect(users.create_login_url(self.request.uri))

class ShowItemHandler(Handler):
    def get(self, item_id):
        tshirt = get_one_tshirt(item_id)
        self.render("show_tshirt.html", tshirt = tshirt)

class AboutHandler(Handler):
    def get(self):
        self.render("about.html")

class SecureHandler(Handler):
    def get(self):
        if users.get_current_user():
            self.write("Welcome to secure page. session value= %s" % self.session.get("foo"))
        else:
            self.write("you need to login to see this page")

class LogoutHandler(Handler):
    def get(self):
        self.response.headers.add_header('Set-Cookie', 'session=; Path=/')
        self.redirect(users.create_logout_url('/'))

class AddToCartHandler(Handler):
    def get(self):
        if users.get_current_user():
            self.response.headers['Content-type'] = 'application/json'
            get_current_add_count = int(self.session.get('add_to_cart_count'))
            tshirt_id = self.request.get("tshirt_id")
            item_title = self.request.get("item_title")
            qty = self.request.get("qty")
            size = self.request.get("size")
            price = 325
            get_current_add_count += 1
            self.session[get_current_add_count] = { "qty" : qty, "size" : size ,
                                                    "item_title": item_title, 
                                                    "tshirt_id" : tshirt_id,
                                                    "cost" : price * int(qty)}

            current_cart_items = int(self.session.get("item_count"))
            updated_cart_items = current_cart_items + int(qty)
            self.session["item_count"] = updated_cart_items
            self.session["add_to_cart_count"] = get_current_add_count
            self.write(json.dumps({"status" : 1, "msg" : "Order added. <a href='/cart'><span class='label label-success'>View Cart</span></a>"}))
        else:
            self.write(json.dumps({"status" : 0, "msg" : "Please <a href='/login'><span class='label label-important'>login</span> </a>to start shopping!"}))


class CartHandler(Handler):
    def get(self):
        item_list = self.get_items_from_cart()
        self.render('show_cart.html', item_list = item_list)

class CheckoutHandler(Handler):
    def get(self):
        item_list = self.get_items_from_cart()
        user = users.get_current_user()
        if user:
            user_email = user.email()
            if item_list:
                for i in item_list:
                    order = Order(qty = int(i["qty"]), 
                                  user_email = user_email,
                                  size = i["size"],
                                  tshirt_id = int(i["tshirt_id"]))
                    order.put()
                    logging.error("Attempt to put in database")
            else:
                logging.error("Updation to Order Model missed")
        else:
            self.redirect('/')
        logging.error("Order Added for user: %s" % user.email())
        self.session["add_to_cart_count"] = 0
        self.redirect('/done')

class DoneHandler(Handler):
    def get(self):
        self.response.headers.add_header('Set-Cookie', 'session=; Path=/')
        self.write("Your order has been recorded. You shortly hear from us regarding payment and delivery details. Thanks for ordering. <a href='/'>Continue shopping</a>")
        
### ADMIN FUNCTIONS ### - Not protected currently
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
        tshirts = get_tshirts()
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


class EmailHandler(Handler):
    def get(self):
        sender_address = "prakhar1989@gmail.com"
        user_address = "kumarar2013@iimcal.ac.in"
        subject = "Hi, from Jokastore"
        body = "Thanks for purchasing from Jokastore"
        mail.send_mail(sender_address, user_address, subject, body)


class ListOrdersHandler(Handler):
    def get(self):
        orders = db.GqlQuery("SELECT * FROM Order ORDER BY time_of_order")
        self.response.headers['Content-type'] = 'text/plain'
        self.render("list_orders.html", orders = orders)

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/logout', LogoutHandler),
                               ('/login', LoginHandler), 
                               ('/item/add', AddItemHandler), 
                               ('/item/edit', EditItemHandler), 
                               ('/cart/add', AddToCartHandler),
                               ('/about', AboutHandler),
                               ('/done', DoneHandler),
                               ('/mainpage', MainPage),
                               ('/cart', CartHandler),
                               ('/all.json', JSONHandler),
                               ('/checkout', CheckoutHandler),
                               ('/sendmail', EmailHandler),
                               ('/listorders', ListOrdersHandler),
                               ('/secure', SecureHandler),
                               ('/tshirt/(\d+)', ShowItemHandler)], config=config, debug=True)
