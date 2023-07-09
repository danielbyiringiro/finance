import csv
import datetime
import pytz
import requests
import subprocess
import urllib
import uuid
import string

from flask import redirect, render_template, session
from functools import wraps
from cs50 import SQL

db = SQL("sqlite:///finance.db")

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Prepare API request
    symbol = symbol.upper()
    end = datetime.datetime.now(pytz.timezone("US/Eastern"))
    start = end - datetime.timedelta(days=7)

    # Yahoo Finance API
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote_plus(symbol)}"
        f"?period1={int(start.timestamp())}"
        f"&period2={int(end.timestamp())}"
        f"&interval=1d&events=history&includeAdjustedClose=true"
    )

    # Query API
    try:
        response = requests.get(url, cookies={"session": str(uuid.uuid4())}, headers={"User-Agent": "python-requests", "Accept": "*/*"})
        response.raise_for_status()

        # CSV header: Date,Open,High,Low,Close,Adj Close,Volume
        quotes = list(csv.DictReader(response.content.decode("utf-8").splitlines()))
        quotes.reverse()
        price = round(float(quotes[0]["Adj Close"]), 2)
        return {
            "name": symbol,
            "price": price,
            "symbol": symbol
        }
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def current_time():
    current_datetime = datetime.datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_datetime

def max_number_shares(share, userID):
    count = db.execute("select sum(number) as num from buy where symbol = ? and buyer_id = ?", share, userID)
    sold = db.execute("select sum(number) as num from sell where symbol = ? and seller_id = ?", share, userID)
    count = count[0]["num"]
    sold = sold[0]["num"]
    if count is None: count = 0
    if sold is None: sold = 0
    remaining_shares = count - sold
    return int(remaining_shares)

def validate(password):
    if len(password) < 8:
        return "Password has to be at least 8 characters"
    passList = list(password)
    numOfnumbers = len([x for x in passList if x.isdigit()])
    numOflower = len([x for x in passList if x.islower()])
    numupper = len([x for x in passList if x.isupper()])
    numOfsymbols = len([x for x in passList if x in string.punctuation])
    if numOfnumbers == 0 or numOflower == 0 or numupper == 0 or numOfsymbols== 0:
        return "Password has to contain at least one number one lowercase one uppercase and one symbol"
    return True

if validate("December5") == True:
    print("Hello")


