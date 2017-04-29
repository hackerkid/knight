from __future__ import print_function

import os
import datetime

from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify
import peewee
from peewee import *
import requests
from newspaper import Article
import newspaper
from keras.models import load_model
from sklearn.externals import joblib
from keras.preprocessing import sequence
import re
from nltk.corpus import stopwords
from bs4 import BeautifulSoup
from gevent.pywsgi import WSGIServer
import language_check
import h5py
from urllib.parse import urlparse

CLIENT_ID = "299591701106-cor2f1c6updmd3dq3pjg5er1evcus7ed.apps.googleusercontent.com"
app = Flask(__name__)
app.config.from_object(__name__) 
app.config.from_pyfile('knight_settings.cfg', silent=True)
db = MySQLDatabase(app.config['DB_NAME'], host=app.config['DB_HOST'], user=app.config['DB_USER'], password=app.config['DB_PASSWORD'])
tk = joblib.load('models/tokenizer.pkl')
tensorflow_model = None
tool = language_check.LanguageTool('en-US')

def news_to_wordlist(news_text, remove_stopwords=False):
	news_text = BeautifulSoup(news_text).get_text()
	news_text = re.sub("[^a-zA-Z]"," ", news_text)
	words = news_text.lower().split()

	if remove_stopwords:
		stops = set(stopwords.words("english"))
		words = [w for w in words if not w in stops]
	return(words)

def get_news_status_from_score(ml_score, grammar_mismatch, total_reports):
    ml_score = ml_score * 100

    if ml_score > 75:
        return "fake"

    if total_reports > 100:
        return "fake"

    if grammar_mismatch > 150:
        return "fake"

    if ml_score > 50:
        return "mostly-fake"

    if total_reports > 20:
        return "mostly-fake"

    if ml_score > 20:
        return "mostly-true"

    return "true"

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    username = CharField()
    full_name = CharField()
    password = CharField()
    email = CharField(unique=True)
    join_date = DateTimeField()
    class Meta:
        order_by = ('email',)

class Report(BaseModel):
    url = peewee.TextField()
    date = peewee.DateTimeField()
    user = ForeignKeyField(User)


@app.cli.command('createtable')
def create_tables():
    db.connect()
    db.create_tables([User, Report])

def get_current_user():
    if session.get('logged_in'):
        return User.get(email=session['email'])

def deep_learn_results(article_body):
    maxlen = 400
    clean_test_news_texts = []
    clean_test_news_texts.append(" ".join(news_to_wordlist(article_body, True)))
    x = tk.texts_to_sequences(clean_test_news_texts)
    x = sequence.pad_sequences(x, maxlen=maxlen)
    return tensorflow_model.predict(x)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if (request.form['auth'] == 'google'):
                token = request.form['token']
                r = requests.post("https://www.googleapis.com/oauth2/v3/tokeninfo", data={"id_token": token})
                if (r.status_code != 200):
                    error = "ivalid token"
                    return render_template('error.html', error=error)
                else:
                    data =  r.json()
                    email = data["email"]
                    full_name = data["name"]
                try:
                    user = User.get(email=email)
                except User.DoesNotExist:
                    user = User(email=email, username="", full_name=full_name, join_date=datetime.datetime.now())
                    user.save()
                session['logged_in'] = True
                session['email'] = user.email
                session['full_name'] = user.full_name
                return jsonify("logged in")
        else:
            try:
                user = User.get(email=request.form['email'], password=request.form['password'])
            except User.DoesNotExist:
                error = 'Invalid login'
                flash('Invalid login')
            else:
                session['logged_in'] = True
                session['email'] = user.email
                flash('You were logged in')
                return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

@app.route('/')
def show_entries():
    return render_template('show_entries.html', reports=Report.select())

@app.route('/info')
def show_info():
    return render_template('show_info.html', reports=Report.select())

@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    new_entry = Report(url=request.form['url'], date=datetime.datetime.now(), user=get_current_user())
    new_entry.save()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))

@app.route('/api/article/info', methods=['POST', 'GET'])
def get_article_info():
    
    if (request.method == "POST"):
        url = request.form['url']
    
    if (request.method == "GET"):
        url = request.args.get('url')
    
    is_article = True
    ml_score = 0.0
    article_authors = None
    article_keywords = None
    article_summary = None
    grammar_mismatch = 0
    total_reports = 0

    article = Article(url)
    article.download()
    try:
        article.parse()
    except newspaper.article.ArticleException:
        is_article = False
    else:
        article_text = article.text
        ml = deep_learn_results(article_text)
        ml_score = float(ml[0][0])
        article_authors = article.authors
        article.nlp()
        article_keywords = article.keywords
        article_summary = article.summary
        grammar_mismatch = len(tool.check(article_text))
    
    try:
        total_reports = Report.select().where(Report.url==url).count()
    except Report.DoesNotExist:
        total_reports = 0

    news_status = get_news_status_from_score(ml_score, grammar_mismatch, total_reports)

    return jsonify({"is_article": is_article, "total_reports": total_reports,
                     "ml_score": ml_score, "authors": article_authors,
                     "keywords": article_keywords, "summary": article_summary,
                     "grammar_mismatch": grammar_mismatch,
                     "news_status": news_status,
                     "title": article.title,
                     "image": article.top_image})

@app.route('/api/report/add', methods=['POST'])
def new_report():
    if not session.get('logged_in'):
        parsed_uri = urlparse(request.url)
        domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        return "Please login <a href='" + domain "'>here</a>." 
    try:
        old_entry = Report.get(url=request.form['url'], user=get_current_user())
    except Report.DoesNotExist:
        new_entry = Report(url=request.form['url'], date=datetime.datetime.now(), user=get_current_user())
        new_entry.save()
        return "The story has been reported." 
    return "You already reported this story"

def initialize():
    global tensorflow_model
    tensorflow_model = load_model('models/tensorflow.h5')

def run(host='0.0.0.0', port=5000):
    """
    run a WSGI server using gevent
    """
    print('running server http://{0}'.format(host + ':' + str(port)))
    WSGIServer((host, port), app).serve_forever()
