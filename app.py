import sqlite3
import string
import urllib2
from math import floor
from sqlite3 import OperationalError
from urlparse import urlparse

from BeautifulSoup import BeautifulSoup
from flask import Flask, request, render_template, redirect, flash

host = 'http://localhost:5000/'

app = Flask(__name__)
app.database = 'example.db'
app.secret_key = 'super secret key'


def createTable():
    create_table = '''CREATE TABLE IF NOT EXISTS WEB_URL (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url string NOT NULL UNIQUE,
        short string,
        hits INT,
        t TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,
        title string
        ); '''

    with sqlite3.connect('example.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(create_table)
        except OperationalError:
            pass


def toBase62(num, b=62):
    if b <= 0 or b > 62:
        return 0
    base = string.digits + string.lowercase + string.uppercase
    r = num % b
    res = base[r]
    q = floor(num / b)
    while q:
        r = q % b
        q = floor(q / b)
        res = base[int(r)] + res
    return res


def toBase10(num, b=62):
    base = string.digits + string.lowercase + string.uppercase
    limit = len(num)
    res = 0
    for i in xrange(limit):
        res = b * res + base.find(num[i])
    return res


def getTitle(url):
    try:
        soup = BeautifulSoup(urllib2.urlopen(url))
        return soup.title.string
    except:
        return None


def validateURL(url):
    parse = urlparse(url)
    if parse.scheme and parse.netloc:
        return True

    return False

####################################################################################################################################################################


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        original_url = request.form.get('url')

        if urlparse(original_url).scheme == '':
            original_url = 'http://' + original_url

        if original_url == "http://":
            return render_template('home.html',
                                   error="Sorry, can't be shorter than this")

        with sqlite3.connect('example.db') as conn:
            cursor = conn.cursor()
            x = conn.execute("SELECT count(*) FROM WEB_URL;")
            sort_str = x.fetchall()[0][0]
            title = getTitle(original_url)
            sort = int(sort_str) + 1
            encoded_string = host + toBase62(sort)

            try:
                cursor.execute(
                    'INSERT INTO WEB_URL (url, short, hits, title) VALUES (?, ?, ?, ?) ',
                    [original_url, encoded_string, 0, title])

            except:
                cursor.execute("SELECT short FROM WEB_URL WHERE url = ?",
                               (original_url, ))
                res = cursor.fetchall()[0][0]
                return render_template('home.html', short_url=res)

        return render_template('home.html', short_url=encoded_string)

    return render_template('home.html')


@app.route('/<short_url>')
def redirect_short_url(short_url):
    decoded_string = toBase10(short_url)

    with sqlite3.connect('example.db') as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE WEB_URL SET hits=(hits+1) WHERE id = ?",
                       (decoded_string, ))
        cursor.execute("SELECT url FROM WEB_URL WHERE id = ?",
                       (decoded_string, ))

        try:
            orignal_url = cursor.fetchall()[0][0]

        except:
            return render_template('home.html',
                                   error="This short URL doesn't exist")

    return redirect(orignal_url)


@app.route('/search', methods=['GET', 'POST'])
def search():
    error = None

    if request.method == 'POST':
        searchStr = request.form.get('search')

        with sqlite3.connect('example.db') as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("SELECT url FROM WEB_URL WHERE title LIKE ? ",
                               ('%' + searchStr + '%', ))

            except:
                pass

        url = [i[0] for i in cursor.fetchall()]

        if not url and searchStr:
            flash("Nope, nothing to see here :(")

        if searchStr:
            return render_template('search.html', url=url)
        flash("The field can't be empty :\\")

    return render_template('search.html', error=error)


@app.route('/hits', methods=['GET', 'POST'])
def hits():
    if request.method == 'POST':
        searchStr = request.form.get('search')
        if searchStr[:4] != 'http':
            searchStr = 'http://' + searchStr

        with sqlite3.connect('example.db') as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT hits FROM WEB_URL WHERE short = ? ",
                               (searchStr, ))
            except:
                pass
        try:
            hits = cursor.fetchall()[0][0]
            print hits

        except:
            return render_template('hits.html', error="URL not available")

        return render_template('hits.html', url=hits)

    return render_template('hits.html')


if __name__ == '__main__':
    createTable()
    app.run(debug=True)