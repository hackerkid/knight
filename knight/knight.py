import os
import datetime

from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify
import peewee
from peewee import *

app = Flask(__name__)
app.config.from_object(__name__) 
app.config.from_pyfile('knight_settings.cfg', silent=True)

db = MySQLDatabase(app.config['DB_NAME'], host=app.config['DB_HOST'], user=app.config['DB_USER'], password=app.config['DB_PASSWORD'])

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    email = CharField()
    join_date = DateTimeField()

    class Meta:
        order_by = ('username',)

class Report(BaseModel):
    url = peewee.TextField()
    date = peewee.DateTimeField()
    user = ForeignKeyField(User)

@app.cli.command('createtable')
def create_tables():
    db.connect()
    db.create_tables([User, Report])

@app.route('/')
def show_entries():
    return render_template('show_entries.html', reports=Report.select())

@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    new_entry = Report(url=request.form['url'], date=datetime.datetime.now(), user=get_current_user())
    new_entry.save()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))

def get_current_user():
    if session.get('logged_in'):
        return User.get(username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        try:
            user = User.get(username=request.form['username'], password=request.form['password'])
        except User.DoesNotExist:
            error = 'Invalid login'
            flash('Invalid logins')
        else:
            session['logged_in'] = True
            session['username'] = user.username
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

@app.route('/api/article_info', methods=['POST'])
def get_article_info():
    errors = []
    try:
        url = request.form['url']
    except:
        errors.append(
            'Something went wrong while fetching the article info'
        )
        abort(401)
    
    return jsonify({'url': url}) 