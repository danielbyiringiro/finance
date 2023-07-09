import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, current_time, max_number_shares, validate

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    shares = db.execute("select distinct symbol from buy where buyer_id = ?", session["user_id"])
    temp = []
    for share in shares:
        temp.append(share["symbol"])
    shares = []
    for share in temp:
        remaining_shares = max_number_shares(share,session["user_id"])
        if remaining_shares == 0 : continue
        price = float(lookup(share)["price"])
        total = remaining_shares * price
        entry = {"share":share,"name":share,"shares":remaining_shares,"price":price, "total": total}
        shares.append(entry)
    cash = db.execute("SELECT cash from users where id = ?", session["user_id"])
    cash = float(cash[0]["cash"])
    username = db.execute("select username from users where id = ?", session["user_id"])
    username = username[0]["username"]
    return render_template("index.html", transactions = shares, cash = cash, username = username)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        username = db.execute("select username from users where id = ?", session["user_id"])
        username = username[0]["username"]
        return render_template("buy.html", username=username)
    elif request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Symbol is empty")
        details = lookup(symbol)
        if details is None:
            return apology("Invalid Symbol")
        price = float(details["price"])
        number = request.form.get("number")
        number = int(number)
        if number <= 0:
            return apology("Invalid Number")
        symbol = symbol.upper()
        totalCost = price * number
        cash = db.execute("SELECT cash from users where id = ?", session["user_id"])
        cash = float(cash[0]["cash"])
        if totalCost > cash : return apology("can't afford")
        balance = cash - totalCost
        time = current_time()
        db.execute("INSERT INTO buy(buyer_id,symbol,number,time,price) VALUES(?,?,?,?,?)", session["user_id"],symbol,number,time,price)
        db.execute("UPDATE users SET cash = ? where id = ?",balance,session["user_id"])
        flash("Bought!","success")
        return redirect("/")



@app.route("/history")
@login_required
def history():
    buys = db.execute("SELECT id,symbol, number, price, time from buy where buyer_id = ?", session["user_id"])
    sales = db.execute("SELECT id,symbol, number, price, time from sell where seller_id = ?", session["user_id"])
    transactions = []
    for transaction in buys:
       symbol = transaction["symbol"]
       number = transaction["number"]
       price = transaction["price"]
       time = transaction["time"]
       entry = {"symbol":symbol,"number":number,"price":price,"time":time}
       transactions.append(entry)
    
    for transaction in sales:
       symbol = transaction["symbol"]
       number = 0 - int(transaction["number"])
       price = transaction["price"]
       time = transaction["time"]
       entry = {"symbol":symbol,"number":number,"price":price,"time":time}
       transactions.append(entry)
    username = db.execute("select username from users where id = ?", session["user_id"])
    username = username[0]["username"]
    return render_template("history.html", transactions = transactions, username = username)
    


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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        username = db.execute("select username from users where id = ?", session["user_id"])
        username = username[0]["username"]
        return render_template("quote.html",username = username)
    elif request.method == "POST":
        symbol = request.form.get("quote")
        details = lookup(symbol)
        if not symbol or details is None:
            return apology("Invalid Symbol")
        return render_template("quoted.html", quoteDetails=details)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    
    elif request.method == "POST":
        username = request.form.get("username")
        rows = db.execute("SELECT * FROM users where username = ?", username)
        if len(rows) != 0 or not username:
            flash("Username already taken","error")
            return apology("Username taken or empty submission")
        
        password, confirmation = request.form.get("password"), request.form.get("confirmation")
        if validate(password) != True:
            message = validate(password)
            flash(message,"error")
            return apology(message)
        if not password or not confirmation or password != confirmation:
            flash("Passwords do not match","error")
            return apology("Passwords do not match")
        password_hash = generate_password_hash(password)
        db.execute("INSERT INTO users(username,hash) VALUES(?,?)", username, password_hash)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = rows[0]["id"]
        flash("Registered!","success")
        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    
    if request.method == "GET":
        shares = db.execute("SELECT distinct(symbol) FROM users JOIN buy ON users.id = buy.buyer_id where users.id = ?", session["user_id"])
        symbols = []
        for i in range(len(shares)):
            share = shares[i]["symbol"]
            share = share.upper()
            symbols.append(share)
        return render_template("sale.html", shares=symbols)
    
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("empty symbol")
        max_shares = max_number_shares(symbol,session["user_id"])
        print(f"Max Shares is {max_shares}")
        number = int(request.form.get("shares"))
        if number <= 0:
            return apology("negative shares")
        if number > max_shares:
            return apology("too many shares")

        price_per_share = float(lookup(symbol)["price"])
        totalCost = price_per_share * number
        cash = db.execute("select cash from users where id = ?", session["user_id"])
        cash = float(cash[0]["cash"])
        cash += totalCost
        time = current_time()
        db.execute("INSERT INTO sell(seller_id,symbol,number,time,price) VALUES(?,?,?,?,?)",session["user_id"],symbol,number,time,price_per_share)
        db.execute("UPDATE users SET cash = ? where id = ?", cash, session["user_id"])
        flash("Sold!","success")
        return redirect("/")

@app.route("/<username>")
@login_required
def user_profile(username):
    name = username
    cash = db.execute("select cash from users where username = ?", name)
    cash = cash[0]["cash"]
    entry = {"name" : name,"cash": cash}
    return render_template("profile.html", entry = entry)

@app.route("/change", methods = ["GET","POST"])
@login_required
def change():
    if request.method == "GET":
        return render_template("change.html", id = session["user_id"])
    else:
        oldPassword = request.form.get("old")
        newPassword = request.form.get("new")
        newPasswordConfirm = request.form.get("newconfirm")
        id = request.form.get("id")

        passwordHash = generate_password_hash(newPassword)
        currentPassword = db.execute("select hash from users where id = ?", id)
        currentPassword = currentPassword[0]["hash"]
        
        print(oldPassword)
        print(id)
        if not check_password_hash(currentPassword, oldPassword):
            flash("Wrong old password", "error")
            return redirect("/change")
        
        if validate(newPassword) != True:
            message = validate(newPassword)
            flash(message,"error")
            return redirect("/change")
        
        if newPassword != newPasswordConfirm:
            flash("Passwords do not match", "error")
            return redirect("/change")
        
        db.execute("UPDATE users SET hash = ? where id = ?", passwordHash, id)
        flash("Password successfully changed", "success")
        return redirect("/")


