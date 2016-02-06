#-*- coding:utf-8 -*-
import os
import random
from flask import Flask, render_template, redirect, url_for, request, g

## import sqlalchemy
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

## import flask-login
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user

## import hashlib
import hashlib
import json
import pusher


## create flask app
app = Flask(__name__)

## debug mode set true
app.debug = True

## configuration database uri. this can be changed for 'mysql' 'postgresql' and so on.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/ubuntu/workspace/mydb.db'

## set a secret
app.config['SECRET_KEY'] = 'asjdfiaj49wifajds0j3'

## create(initialize) sqlalchemy 
db = SQLAlchemy(app)

## create login manager
login_manager = LoginManager()
login_manager.init_app(app)


### declare models
class User(db.Model): ## user model.
    ## user has ID, password, name, age  
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.VARCHAR(256))
    password = db.Column(db.VARCHAR(256))
    age = db.Column(db.Integer)
    
    created = db.Column(db.DateTime, default=datetime.now())
    
    guestbooks = db.relationship('Guestbook', backref='author', lazy='dynamic')
    
    def is_authenticated(self):
        
        return True
    
    def is_active(self):
        return True
        
    def get_id(self):
        return unicode(self.id)
    
class Guestbook(db.Model): ## guest book model.
    id = db.Column(db.Integer, primary_key=True)
    guest_name = db.Column(db.VARCHAR(256))
    contents = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.now())
    likes = db.Column(db.Integer, default=0)
    
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    
## preprocess
@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.before_request
def before_request():
    g.user = current_user
    
@login_manager.unauthorized_handler
def unauthorized():
    # do stuff
    return redirect(url_for('index_page'))

### declare controllers
## route '/'
@app.route('/', methods=['GET','POST'])
def index_page():
    if request.method == 'GET':
        ## if logined
        if g.user.is_authenticated:
            return redirect(url_for('guest_book'))
        
        ## query(get) data
        # User : model class
        # User.query : query for model 'User'
        # User.query.filter(User.age>=20).order_by(User.age.desc()) : query by filtering 'age >= 20' and order by age descending.
        users = User.query.filter(User.age>=20).order_by(User.age.desc())
        
        ## render to index.html with 'users'
        return render_template('index.html', users = users)
    elif request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        
        ## hash password
        password = hashlib.sha224(password).hexdigest()
        
        ## find user and check password
        user = User.query.filter_by(name=name, password=password).first()
        if user:
            ## session save
            login_user(user)
            
    ## if you're not 'get' request, just go to 'def index_page' (GET)
    return redirect(url_for('index_page'))


## route '/signup'
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')    
    elif request.method == 'POST':
         ## get form data (username, age)
        username = request.form['username']
        password = request.form['password']
        age = request.form['age']
        
        ## hash the password 
        password = hashlib.sha224(password).hexdigest()
        
        ## check duplicate
        if User.query.filter_by(name=username).first():
            return redirect(url_for('signup'))
        
        ## insert data from form
        user = User(name=username, password=password, age=age, created=datetime.now())
        
        ## just add a item database session 
        db.session.add(user)
        
        ## adjust database session (actually, added)
        db.session.commit()
        
        return redirect(url_for('index_page'))
    
    return redirect(url_for('index_page'))

## route '/guest'
@app.route('/guest', methods=['GET','POST'])
@login_required
def guest_book():
    if request.method == 'GET':
        ## query(get) data, sort by created. (descending)
        books = Guestbook.query.order_by(Guestbook.created.desc())
        
        ## render books.html 
        return render_template('books.html', books = books)
    elif request.method == 'POST':
        
        ## get form data
        author_id = request.form['author_id']
        guestname = request.form['guest_name']
        contents = request.form['contents']
        
        ## insert data
        guestbook = Guestbook(guest_name = guestname, contents = contents, author_id=author_id, created = datetime.now())
        db.session.add(guestbook)
        db.session.commit()
    
    ## redirecting...
    return redirect(url_for('guest_book'))  

## route '/guest/update'
@app.route('/guest/update', methods=['GET','POST'])
def guest_update():
    if request.method == 'GET':
        ## query(get) data, find book by id
        book_id = request.args['book_id']
        book = Guestbook.query.get(int(book_id))
        
        ## render html 
        return render_template('book_update.html', book = book)
    elif request.method == 'POST':
        
        ## get form data
        book_id = request.form['book_id']
        author_id = request.form['author_id']
        guestname = request.form['guest_name']
        contents = request.form['contents']
        
        ## modifiying
        book = Guestbook.query.get(int(book_id))
        book.author_id = author_id
        book.guest_name = guestname
        book.contents = contents
    
        db.session.commit()
    
    ## redirecting...
    return redirect(url_for('guest_book'))  

@app.route('/guest/delete')
@login_required
def guest_delete():
    book_id = request.args['book_id']
    book = Guestbook.query.get(int(book_id))
    if book:
        ##Guestbook.query.filter_by(id=book.id).delete()
        db.session.delete(book)
        db.session.commit()
    
    return redirect(url_for('guest_book'))
    


@app.route('/logout')
@login_required
def logout():
    logout_user()
    
    return redirect(url_for('index_page'))
    
## likes request
@app.route('/like')
def like_guest():
    ### /like?id=2
    guest_id = request.args['id']
    book = Guestbook.query.filter_by(id=guest_id).first()
    book.likes = book.likes + 1
    db.session.commit()
    
    return json.dumps({
        'id':book.id,
        'likes':book.likes
    })

## chat message send
@app.route('/message', methods=['POST'])
def send_message():
    p = pusher.Pusher(
      app_id='174869',
      key='fbbabfbe03c4fb3e5129',
      secret='32614cdb5e0737ae64f9',
      ssl=True,
      port=443
    )
    p.trigger('chats', 'new_message', {'message': request.form['message']})
    
    return json.dumps({
        'success':True
    })

        
        
### run flask app
if __name__ == '__main__':
    app.run(host=os.getenv('IP','0.0.0.0'), port=int(os.getenv('PORT',8080)))