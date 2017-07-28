from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from data import Articles
from flaskext.mysql import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from config import DotDict, dateToEnglish
from functools import wraps
import os
from werkzeug.utils import secure_filename

# init app
app = Flask(__name__)

# Upload folder
UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['mp3', 'm4a', 'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Config MySQL
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
# app.config['MYSQL_DATABASE_PORT'] = '3306'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'thomas_blog'

# init MYSQL
mysql = MySQL()
mysql.init_app(app)

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap
# Home Page
@app.route('/')
def index():
    # By default render_template looks in the '/templates/' dir
    return render_template('home.html')

# About Page
@app.route('/about')
def about():
    return render_template('about.html')


# File Upload Page
@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():

    return render_template('upload_file.html')

# All Articles
@app.route('/articles')
def articles():
    # Create cursor
    cur = mysql.get_db().cursor()
    # Get articles
    result = cur.execute("SELECT * FROM articles")
    # articles = cur.fetchall()
    articles = dictArrayFromCursor(cur)
    # Sort articles by date, newest first.
    sorted_articles = sorted(articles, key=lambda k: k['create_date'], reverse = True)
    cur.close()
    # Check results
    if result > 0:
        return render_template('articles.html', articles=sorted_articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)

# Single Article
@app.route('/article/<string:id>/')
def article(id):
    # Create cursor
    cur = mysql.get_db().cursor()
    # Get articles
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    # Get first (and only) element from result (0th element)
    article = dictFromCursor(cur)
    # Set date to something readable by humans
    article.create_date = dateToEnglish(article.create_date, 'yyyy-mm-dd')

    cur = mysql.get_db().cursor()
    cur.execute("SELECT * FROM users wHERE username = %s", [article.author])
    user = dictFromCursor(cur)
    # Render the page
    return render_template('article.html', article=article, user=user)

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.get_db().cursor()
        # Execute query
        cur.execute("INSERT INTO users (name, email, username, password) VALUES (%s, %s, %s, %s)", (name, email, username, password))
        # Commit to DB
        mysql.get_db().commit()
        # Close connection
        cur.close()
        # Registration success
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Log in
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)

    if request.method == 'POST':
        username = form.username.data
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.get_db().cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])
        if result > 0:
            # Get stored hash, from the first user to appear in query
            data = dictFromCursor(cur)
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Credentials Correct
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                # Credentials Wrong
                error = 'Invalid login'
                return render_template('login.html', error=error, form=form)

            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error, form=form)

    return render_template('login.html', form=form)

# Log out
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.get_db().cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")

    articles = dictArrayFromCursor(cur)

    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cur.close()

# Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    # Acquire the HTML form for writing an article
    form = ArticleForm(request.form)

    # Check if trying to submit
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create Cursor
        cur = mysql.get_db().cursor()
        user = session['username']
        # Execute
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, user))

        # Commit to DB
        mysql.get_db().commit()

        #Close connection
        cur.close()

        flash('Article Created', 'success')

        # Redirect to dashboard, to show the new article
        return redirect(url_for('dashboard'))

    # If user is not attempting to add a new article, render the page
    return render_template('add_article.html', form=form)

# Edit Article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # Create cursor
    cur = mysql.get_db().cursor()

    # Get article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = dictFromCursor(cur)
    cur.close()
    # Get form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article.title
    form.body.data = article.body

    # If user is trying to submit
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create Cursor
        cur = mysql.get_db().cursor()
        app.logger.info(title)
        # Execute
        cur.execute ("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))
        # Commit to DB
        mysql.get_db().commit()

        #Close connection
        cur.close()

        flash('Article Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

# Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # Create cursor
    cur = mysql.get_db().cursor()

    # Execute
    cur.execute("DELETE FROM articles WHERE id = %s", [id])

    # Commit to DB
    mysql.get_db().commit()

    #Close connection
    cur.close()

    flash('Article Deleted', 'success')

    return redirect(url_for('dashboard'))

# AUX FUNCTIONS
def dictArrayFromCursor(cur):
    # Get column names, i.e. id, name, username etc from metadata
    columns = [meta[0] for meta in cur.description]
    data = cur.fetchall()
    # Make a DotDict (in config file) with each article
    return [DotDict(dict(zip(columns, x))) for x in data]

def dictFromCursor(cur):
    # Return the first element in Dict Array
    return dictArrayFromCursor(cur)[0]

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# CLASSES
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
     validators.DataRequired(),
     validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

class LoginForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    password = PasswordField('Password', [validators.DataRequired()])

class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])

# MAIN SCRIPT
if __name__ == '__main__':
    # Key is necessary for sha
    app.secret_key = "secret123"
    app.run(debug = True)
