#used finance.db as guidance for import statements, configuring the web application, and login/logout functions

import os
import webbrowser
import re
import socket

from jinja2 import Template
from PIL import Image
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

from flask import Flask
from flask_mail import Mail, Message


# Configure application
app = Flask(__name__)

# Requires that "Less secure app access" be on
# https://support.google.com/accounts/answer/6010255
#app.config["MAIL_DEFAULT_SENDER"] = os.environ["MAIL_DEFAULT_SENDER"]
#app.config["MAIL_PASSWORD"] = os.environ["MAIL_PASSWORD"]
app.config["MAIL_PORT"] = 587
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_USE_TLS"] = True
#app.config["MAIL_USERNAME"] = os.environ["MAIL_USERNAME"]
mail = Mail(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///roots.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/search")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")



@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    if request.method == "POST":

        stylist = request.form.get("stylist")
        hair_style = request.form.get("style")
        hair_type = request.form.get("hair_type")
        users = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        post = db.execute("SELECT * FROM post")
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]['username']
        location_user = request.form.get("location_user")
        return render_template("explore.html",  stylist=stylist, users=users, post=post, username=username, location_user = location_user, hair_style=hair_style, hair_type=hair_type)
    else:
        return render_template("search.html")

@app.route("/profile_user", methods=["GET", "POST"])
@login_required
def profile_user():
    if db.execute("SELECT account_type FROM users WHERE id = ?", session["user_id"])[0]['account_type'] == 1:
        post = db.execute("SELECT * FROM post WHERE id = ?", session["user_id"])
        reviews = db.execute("SELECT * FROM reviews WHERE reviewee_id = ?", session["user_id"])
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]['username']
        return render_template("profile-stylist.html", post=post, reviews=reviews, username=username)
    else:
        reviews = db.execute("SELECT * FROM reviews WHERE reviewer_id = ?", session["user_id"])
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]['username']

        return render_template("profile-user.html", reviews=reviews, username=username)

@app.route("/review", methods=["GET", "POST"])
@login_required
def review():
    if request.method == "POST":
        username = request.form.get("username")
        reviewee_id = db.execute("SELECT id FROM users WHERE username = ?", username)
        reviewee_id= reviewee_id[0]['id']

        rating = request.form.get("rating")
        review = request.form.get("review-text")

        db.execute("INSERT INTO reviews (username, reviewee_id, reviewer_id, rating, comments) VALUES (?, ?, ?, ?, ?)", username, reviewee_id ,session["user_id"], rating, review)
        
        return redirect("/profile_user")

    else:
        return render_template("review.html")


@app.route("/new_post", methods=["GET", "POST"])
@login_required
def new_post():
    if request.method == "POST":
        
        caption = request.form.get("Caption")
        location = request.form.get("Location")
        url = request.form.get("filename")


        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]['username']
            
        db.execute("INSERT INTO post (id, username, image_name, caption, location) VALUES (?, ?, ?, ?, ?)", session["user_id"], username, url, caption, location)
            
        return redirect("/search")
    else:
        return render_template("new-post.html")

@app.route("/book", methods=["GET", "POST"])
@login_required
def book():
    if request.method == "POST":
        username = request.form.get("StylistName")
        email = request.form.get("email")
        recipient = db.execute("SELECT email FROM users WHERE username = ?", username)[0]['email']
        sender = db.execute("SELECT email FROM users WHERE id = ?", session["user_id"])[0]['email']
        subject = "Hair Appointment"
        text = request.form.get("ContactComment")

        subject = subject.replace(' ', '%20')
       


        return render_template("contact.html", recipient=recipient)
    else:
        return render_template("book.html")


@app.route("/")
def home():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user for an account."""

    # POST
    if request.method == "POST":

        # Validate form submission
        if not request.form.get("username"):
            return apology("missing username")
        elif not request.form.get("password"):
            return apology("missing password")
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords don't match")

        # Add user to database
        try:
            id = db.execute("INSERT INTO users (username, hash, email) VALUES(?, ?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")), request.form.get("email"))
        except ValueError:
            return apology("username taken")

        # Log user in
        session["user_id"] = id

        if request.form.get("acc_type") == 'User':
            return redirect("/login")
        if request.form.get("acc_type") == 'Stylist':
            #update SQL table to make account value 1 (stylist)
            db.execute("UPDATE users SET account_type = ? WHERE id = ?", 1, session["user_id"])
            return redirect("/login")


    # GET
    else:
        return render_template("register.html")

app.config['UPLOAD_FOLDER'] = '/uploads'
app.config['MAX_CONTENT_PATH'] = 1000000
	
@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
   if request.method == 'POST':
      f = request.files['file']
      f.save(f.filename)
      completeName = os.path.join('/uploads', f.filename)
      return redirect(url_for('upload_file', name=f.filename))
      return 'file uploaded successfully'

if __name__ == '__main__':
   app.run(debug = True)