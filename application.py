import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps


# Configure application
app = Flask(__name__)


# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///budget.db")


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "GET":
        rows = db.execute("""SELECT SUM(amount) as totalINCOMES
            FROM transactions
            WHERE user_id = :user_id AND amount > 0 AND strftime('%m','now')""",
            user_id=session["user_id"])
        for row in rows:
            totalINCOMES = row["totalINCOMES"]
        rows = db.execute("""SELECT SUM(amount) as totalEXPENSES
            FROM transactions
            WHERE user_id = :user_id AND amount < 0 AND strftime('%m','now')""",
            user_id=session["user_id"])
        for row in rows:
            totalEXPENSES = row["totalEXPENSES"]
        incomes = []
        expenses = []
        rows = db.execute("""SELECT amount, category, note, time
            FROM transactions
            WHERE user_id = :user_id AND amount > 0 AND strftime('%m','now')""",
            user_id=session["user_id"])
        for row in rows:
            incomes.append({"amount": row["amount"], "category": row["category"], "note": row["note"], "time": row["time"]})
        rows = db.execute("""SELECT amount, category, note, time
            FROM transactions
            WHERE user_id = :user_id AND amount < 0 AND strftime('%m','now')""",
            user_id=session["user_id"])
        for row in rows:
            expenses.append({"amount": row["amount"], "category": row["category"], "note": row["note"], "time": row["time"]})
        if not totalINCOMES:
            totalINCOMES = 0
        if not totalEXPENSES:
            totalEXPENSES = 0
        balance = usd(totalINCOMES - totalEXPENSES*-1)
        totalINCOMES = usd(totalINCOMES)
        totalEXPENSES = usd(totalEXPENSES *-1)
        return render_template("index.html", balance=balance, totalINCOMES=totalINCOMES, totalEXPENSES=totalEXPENSES, incomes=incomes,
        expenses=expenses)


@app.route("/annual", methods=["GET", "POST"])
@login_required
def annual():
    if request.method == "GET":
        rows = db.execute("""SELECT SUM(amount) as totalINCOMES
            FROM transactions
            WHERE user_id = :user_id AND amount > 0 AND strftime('%Y','now')""",
            user_id=session["user_id"])
        for row in rows:
            totalINCOMES = row["totalINCOMES"]
        rows = db.execute("""SELECT SUM(amount) as totalEXPENSES
            FROM transactions
            WHERE user_id = :user_id AND amount < 0 AND strftime('%Y','now')""",
            user_id=session["user_id"])
        for row in rows:
            totalEXPENSES = row["totalEXPENSES"]
        incomes = []
        expenses = []
        rows = db.execute("""SELECT amount, category, note, time
            FROM transactions
            WHERE user_id = :user_id AND amount > 0 AND strftime('%Y','now')""",
            user_id=session["user_id"])
        for row in rows:
            incomes.append({"amount": row["amount"], "category": row["category"], "note": row["note"], "time": row["time"]})
        rows = db.execute("""SELECT amount, category, note, time
            FROM transactions
            WHERE user_id = :user_id AND amount < 0 AND strftime('%Y','now')""",
            user_id=session["user_id"])
        for row in rows:
            expenses.append({"amount": row["amount"], "category": row["category"], "note": row["note"], "time": row["time"]})
        rows = db.execute("SELECT balance FROM users WHERE id = :user_id", user_id=session["user_id"])
        balance = rows[0]["balance"]
        if not totalINCOMES:
            totalINCOMES = 0
        if not totalEXPENSES:
            totalEXPENSES = 0
        totalINCOMES = usd(totalINCOMES)
        totalEXPENSES = usd(totalEXPENSES *-1)
        return render_template("annual.html", balance=usd(balance), totalINCOMES=totalINCOMES, totalEXPENSES=totalEXPENSES, incomes=incomes,
        expenses=expenses)


@app.route("/incomes", methods=["GET", "POST"])
@login_required
def incomes():
    """Sell shares of stock"""
    if request.method == "GET":
        rows = db.execute("SELECT balance FROM users WHERE id = :user_id", user_id=session["user_id"])
        balance = rows[0]["balance"]
        return render_template("incomes.html", balance=usd(balance))
    else:
        amount = float(request.form.get("amount"))
        category = request.form.get("category")
        note = request.form.get("note")
        if not amount:
            message = "You must provide amount."
            return render_template("apology.html", message=message)
        if not category:
            message = "You must provide category."
            return render_template("apology.html", message=message)
        rows = db.execute("SELECT balance FROM users WHERE id = :user_id", user_id=session["user_id"])
        balance = rows[0]["balance"]
        updated_cash = balance + amount
        db.execute("UPDATE users SET balance=:updated_cash WHERE id=:id", updated_cash=updated_cash, id=session["user_id"])
        db.execute("""INSERT INTO transactions (user_id, amount, category, note) VALUES (:user_id, :amount, :category, :note)""",
            user_id = session["user_id"],
            amount = amount,
            category = category,
            note = note)
        flash("Added!")
        return redirect("/")


@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    """Sell shares of stock"""
    if request.method == "GET":
        rows = db.execute("SELECT balance FROM users WHERE id = :user_id", user_id=session["user_id"])
        balance = rows[0]["balance"]
        return render_template("expenses.html", balance=usd(balance))
    else:
        amount = float(request.form.get("amount"))
        category = request.form.get("category")
        note = request.form.get("note")
        if not amount:
            message = "You must provide amount."
            return render_template("apology.html", message=message)
        if not category:
            message = "You must provide category."
            return render_template("apology.html", message=message)

        rows = db.execute("SELECT balance FROM users WHERE id = :user_id", user_id=session["user_id"])
        balance = rows[0]["balance"]
        updated_balance = balance - amount
        db.execute("UPDATE users SET balance=:updated_balance WHERE id=:id", updated_balance=updated_balance, id=session["user_id"])
        db.execute("""INSERT INTO transactions (user_id, amount, category, note) VALUES (:user_id, :amount, :category, :note)""",
            user_id = session["user_id"],
            amount = amount * -1,
            category = category,
            note = note)
        flash("Added!")
        return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            message = "You must provide a username"
            return render_template("apology.html", message=message)

        # Ensure password was submitted
        elif not request.form.get("password"):
            message = "You must provide a password"
            return render_template("apology.html", message=message)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            message = "Invalid username and/or password"
            return render_template("apology.html", message=message)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

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


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            message = "You must provide a username."
            return render_template("apology.html", message=message)

        elif not email:
            message = "You must provide an e-mail."
            return render_template("apology.html", message=message)

        elif not password:
            message = "You must provide a password."
            return render_template("apology.html", message=message)

        elif len(password) < 6:
            message = "Your password must contains min 6 characters"
            return render_template("apology.html", message=message)

        elif not confirmation:
            message = "You must provide a password confirmation."
            return render_template("apology.html", message=message)

        elif password != confirmation:
            message = "Passwords do not match."
            return render_template("apology.html", message=message)

        password_hash = generate_password_hash(password)
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        try:
            db.execute("INSERT INTO users (username, email, hash) VALUES (:username, :email, :hash)", username=username, email=email, hash=password_hash)
        except:
            message = "The username already exist"
            return render_template("apology.html", message=message)
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    message = "%s, %s." % (e.name, e.code)
    return render_template("apology.html", message=message)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)