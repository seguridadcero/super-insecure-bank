import os
import sqlite3
import hashlib
import uuid
import json
import subprocess
import logging
import socket
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import Flask, request, redirect, url_for, render_template, make_response, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(DATA_DIR, "super_insecure_bank.db"))
STATEMENTS_DIR = os.path.join(DATA_DIR, "statements")
JWT_SECRET = os.environ.get("JWT_SECRET", "trustno1")

app = Flask(__name__)
app.secret_key = "dev-session-secret"
app.config["DEBUG"] = True
logging.getLogger("werkzeug").setLevel(logging.ERROR)

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATEMENTS_DIR, exist_ok=True)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def md5(value: str) -> str:
    return hashlib.md5(value.encode()).hexdigest()


def log_event(message: str):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "security.log"), "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")


def decode_access_token(token: str):
    if not token:
        return None
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


def current_user():
    """Return the authenticated user from the functional JWT access_token cookie."""
    token = request.cookies.get("access_token")
    data = decode_access_token(token)
    if not data:
        return None
    username = data.get("username")
    if not username:
        return None
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return user


def make_access_token(user):
    return jwt.encode({
        "sub": user["username"],
        "username": user["username"],
        "role": "customer"
    }, JWT_SECRET, algorithm="HS256")


def make_reset_token(username):
    return jwt.encode({
        "sub": username,
        "username": username,
        "purpose": "password_reset"
    }, JWT_SECRET, algorithm="HS256")


def decode_reset_token(token):
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if data.get("purpose") != "password_reset":
            return None
        return data
    except Exception:
        return None


def require_json_body(required_fields=None):
    """Strict JSON-only request parser for business/data-processing endpoints."""
    if not request.is_json:
        return None, (jsonify({"error": "Content-Type must be application/json"}), 415)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "Invalid JSON body"}), 400)
    missing = [f for f in (required_fields or []) if data.get(f) in (None, "")]
    if missing:
        return None, (jsonify({"error": "Missing required fields", "missing": missing}), 400)
    return data, None


def json_error(message, status=400, **extra):
    payload = {"error": message}
    payload.update(extra)
    return jsonify(payload), status


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_layout_context():
    path = request.path or "/"
    if path == "/":
        subsystem = "lab"
        subsystem_name = "Lab Welcome Page"
    elif path.startswith("/mailbox"):
        subsystem = "mail"
        subsystem_name = "Mock Mail Server"
    elif path.startswith("/security-dashboard"):
        subsystem = "logs"
        subsystem_name = "Security Dashboard"
    elif path.startswith("/social"):
        subsystem = "social"
        subsystem_name = "Social Media Mockup"
    else:
        subsystem = "banking"
        subsystem_name = "Banking Application"
    public_banking_paths = {"/login", "/forgot-password", "/reset-password", "/api/reset-password/confirm"}
    show_banking_nav = subsystem == "banking" and current_user() is not None and path not in public_banking_paths
    return {
        "active_user": current_user(),
        "subsystem": subsystem,
        "subsystem_name": subsystem_name,
        "show_banking_nav": show_banking_nav
    }


def last_completed_months(n=3):
    """Return YYYY-MM strings for the last n completed months based on server time."""
    today = datetime.now()
    year = today.year
    month = today.month - 1
    periods = []
    for _ in range(n):
        if month == 0:
            month = 12
            year -= 1
        periods.append(f"{year:04d}-{month:02d}")
        month -= 1
    return periods

def init_db():
    conn = db()
    c = conn.cursor()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            otp_phone TEXT,
            address TEXT,
            occupation TEXT,
            monthly_income TEXT,
            source_of_funds TEXT,
            loan_enabled INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT UNIQUE,
            username TEXT,
            account_type TEXT,
            currency TEXT,
            balance REAL
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transfer_id TEXT,
            from_account TEXT,
            to_account TEXT,
            amount REAL,
            fee REAL,
            currency TEXT,
            description TEXT,
            status TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT,
            username TEXT,
            used INTEGER DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS mails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            subject TEXT,
            body TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id TEXT UNIQUE,
            transfer_id TEXT,
            from_account TEXT,
            to_account TEXT,
            amount TEXT,
            currency TEXT,
            status TEXT,
            created_at TEXT,
            payment_reference TEXT
        );
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            account_id TEXT,
            amount TEXT,
            term_months TEXT,
            status TEXT,
            created_at TEXT
        );
        """
    )
    conn.commit()

    # Lightweight migrations for regenerated lab versions.
    existing_loan_cols = [r["name"] for r in conn.execute("PRAGMA table_info(loans)").fetchall()]
    if "purpose" not in existing_loan_cols:
        conn.execute("ALTER TABLE loans ADD COLUMN purpose TEXT")
    if "currency" not in existing_loan_cols:
        conn.execute("ALTER TABLE loans ADD COLUMN currency TEXT DEFAULT 'USD'")
    if "loan_id" not in existing_loan_cols:
        conn.execute("ALTER TABLE loans ADD COLUMN loan_id TEXT")

    existing_receipt_cols = [r["name"] for r in conn.execute("PRAGMA table_info(receipts)").fetchall()]
    if "payment_reference" not in existing_receipt_cols:
        conn.execute("ALTER TABLE receipts ADD COLUMN payment_reference TEXT")
    conn.commit()

    count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    if count == 0:
        # Passwords are intentionally weak/common for the lab so A04.2 can be demonstrated after SQLi hash extraction.
        users = [
            ("Fernando Conislla", "fernando.conislla", "fernando.conislla@superinsecurebank.com", "password1", "+51 900 111 222", "Av Principal 123", "Consultant", "5000", "Salary", 0),
            ("Alice Morrison", "alice.morrison", "alice.morrison@superinsecurebank.com", "qwerty", "+1 555 0102", "Oak Street 20", "Designer", "6200", "Salary", 0),
            ("Bob Wilson", "bob.wilson", "bob.wilson@superinsecurebank.com", "letmein", "+1 555 0103", "Pine Avenue 14", "Engineer", "5400", "Salary", 0),
            ("Carla Bennett", "carla.bennett", "carla.bennett@superinsecurebank.com", "football", "+1 555 0104", "Maple 19", "Analyst", "4200", "Salary", 0),
            ("Daniel Brooks", "daniel.brooks", "daniel.brooks@superinsecurebank.com", "monkey", "+1 555 0105", "Lake Road 55", "Manager", "7300", "Salary", 0),
            ("Alonso Conislla", "alonso.conislla", "alonso.conislla@superinsecurebank.com", "dragon", "+51 900 222 333", "Hidden 1", "Auditor", "4800", "Salary", 0),
            ("Emily Carter", "emily.carter", "emily.carter@superinsecurebank.com", "abc123", "+1 555 0107", "Hidden 2", "Teacher", "3900", "Salary", 0),
            ("James Howard", "james.howard", "james.howard@superinsecurebank.com", "123456", "+1 555 0108", "Hidden 3", "Developer", "6700", "Salary", 0),
            ("Olivia Martin", "olivia.martin", "olivia.martin@superinsecurebank.com", "password", "+1 555 0109", "Hidden 4", "Nurse", "4100", "Salary", 0),
            ("William Scott", "william.scott", "william.scott@superinsecurebank.com", "123456789", "+1 555 0110", "Hidden 5", "Architect", "7000", "Salary", 0),
        ]
        conn.executemany(
            "INSERT INTO users(full_name,username,email,password_hash,otp_phone,address,occupation,monthly_income,source_of_funds,loan_enabled) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(u[0], u[1], u[2], md5(u[3]), *u[4:]) for u in users]
        )

        account_map = {
            "fernando.conislla": [("1001", "Checking", 5000.00), ("1004", "Savings", 2500.00)],
            "alice.morrison": [("2002", "Checking", 8500.00), ("2005", "Savings", 3200.00)],
            "bob.wilson": [("3003", "Checking", 4300.00), ("3006", "Savings", 1800.00)],
            "carla.bennett": [("4101", "Checking", 3900.00), ("4104", "Savings", 1400.00)],
            "daniel.brooks": [("5101", "Checking", 7200.00), ("5104", "Savings", 2800.00)],
            "alonso.conislla": [("6101", "Checking", 4600.00), ("6104", "Savings", 1600.00)],
            "emily.carter": [("7101", "Checking", 3100.00), ("7104", "Savings", 900.00)],
            "james.howard": [("8101", "Checking", 6800.00), ("8104", "Savings", 2200.00)],
            "olivia.martin": [("9101", "Checking", 3500.00), ("9104", "Savings", 1100.00)],
            "william.scott": [("9901", "Checking", 7600.00), ("9904", "Savings", 3100.00)],
        }
        accounts = []
        for username, items in account_map.items():
            for account_number, account_type, balance in items:
                accounts.append((account_number, username, account_type, "USD", balance))
        conn.executemany("INSERT INTO accounts(account_number,username,account_type,currency,balance) VALUES (?,?,?,?,?)", accounts)

        # Generate active, coherent banking history.
        # IDs increase with dates, and each user has activity on both accounts for the last 3 completed months.
        completed_months = list(reversed(last_completed_months(3)))
        event_rows = []
        receipt_rows = []
        account_numbers = [a[0] for a in accounts]
        for idx, (account_number, username, account_type, currency, balance) in enumerate(accounts):
            peer = account_numbers[(idx + 3) % len(account_numbers)]
            internal_peer = account_map[username][1][0] if account_type == "Checking" else account_map[username][0][0]
            for m_index, period in enumerate(completed_months):
                y, m = map(int, period.split("-"))
                salary_amount = 1800 + ((idx % 5) * 150)
                purchase_amount = 35 + ((idx + m_index) % 7) * 11
                savings_amount = 120 + ((idx + m_index) % 4) * 25
                external_amount = 55 + ((idx + m_index) % 6) * 13
                event_rows.extend([
                    (datetime(y, m, 5, 9, 30), "PAYROLL", account_number, salary_amount, 0.00, "USD", f"Payroll deposit {period}", "APPROVED"),
                    (datetime(y, m, 11, 15, 45), account_number, "MERCHANT-204", purchase_amount, 0.00, "USD", f"Debit card purchase {period}", "APPROVED"),
                    (datetime(y, m, 18, 12, 5), account_number, internal_peer, savings_amount, 0.00, "USD", f"Internal savings movement {period}", "APPROVED"),
                    (datetime(y, m, 24, 16, 20), account_number, peer, external_amount, round(external_amount * 0.01, 2), "USD", f"External transfer {period}", "APPROVED"),
                ])

        # Recent transactions for the visible training accounts; high IDs and recent dates keep ordering natural.
        now = datetime.now().replace(microsecond=0)
        event_rows.extend([
            (now - timedelta(minutes=16), "1001", "2002", 150.00, 1.50, "USD", "Dinner reimbursement", "APPROVED"),
            (now - timedelta(minutes=15), "1001", "3003", 75.00, 0.75, "USD", "Shared subscription", "APPROVED"),
            (now - timedelta(minutes=14), "2002", "2005", 500.00, 0.00, "USD", "Savings transfer", "APPROVED"),
            (now - timedelta(minutes=13), "3003", "3006", 250.00, 0.00, "USD", "Monthly savings", "APPROVED"),
            (now - timedelta(minutes=12), "2002", "1001", 120.00, 1.20, "USD", "Conference expenses", "APPROVED"),
            (now - timedelta(minutes=11), "3003", "2002", 60.00, 0.60, "USD", "Lunch payment", "APPROVED"),
        ])
        event_rows.sort(key=lambda r: r[0])
        tx_rows = []
        transfer_seq = 9001
        for event in event_rows:
            created_at, from_acc, to_acc, amount, fee, currency, description, status = event
            transfer_id = f"T{transfer_seq}"
            tx_rows.append((transfer_id, from_acc, to_acc, amount, fee, currency, description, status, created_at.isoformat()))
            if from_acc != "PAYROLL" and not str(to_acc).startswith("MERCHANT"):
                receipt_rows.append((f"R-{transfer_id}", transfer_id, from_acc, to_acc, f"{amount:.2f}", currency, status, created_at.isoformat()))
            transfer_seq += 1

        conn.executemany(
            "INSERT INTO transactions(transfer_id,from_account,to_account,amount,fee,currency,description,status,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            tx_rows
        )
        conn.executemany(
            "INSERT OR IGNORE INTO receipts(receipt_id,transfer_id,from_account,to_account,amount,currency,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
            receipt_rows
        )
        # Seed a few logs so the dashboard is understandable before the user generates new events.
        log_event("LOGIN_FAILED user=alice.morrison password=Summer2026")
        log_event("LOGIN_SUCCESS user=fernando.conislla jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sample.jwt")
        conn.commit()
    conn.close()
    generate_statements()


def generate_statements():
    """Generate coherent PDF statement fixtures for every account and the last 3 completed months."""
    os.makedirs(STATEMENTS_DIR, exist_ok=True)
    periods = list(reversed(last_completed_months(3)))
    conn = db()
    accounts = conn.execute("SELECT a.*, u.full_name FROM accounts a JOIN users u ON u.username=a.username ORDER BY a.account_number").fetchall()
    for acc in accounts:
        account_dir = os.path.join(STATEMENTS_DIR, acc["account_number"])
        os.makedirs(account_dir, exist_ok=True)
        all_period_txs = conn.execute(
            "SELECT * FROM transactions WHERE (from_account=? OR to_account=?) AND substr(created_at,1,7) IN (%s) ORDER BY created_at ASC, id ASC" % ",".join(["?"] * len(periods)),
            (acc["account_number"], acc["account_number"], *periods)
        ).fetchall()
        def signed_amount(tx):
            if tx["to_account"] == acc["account_number"]:
                return Decimal(str(tx["amount"]))
            if tx["from_account"] == acc["account_number"]:
                return -(Decimal(str(tx["amount"])) + Decimal(str(tx["fee"] or 0)))
            return Decimal("0.00")
        total_net = sum((signed_amount(tx) for tx in all_period_txs), Decimal("0.00"))
        running_balance = Decimal(str(acc["balance"])) - total_net
        for period in periods:
            year, month = period.split('-')
            filename = f"statement_{acc['account_number']}_{month}{year}.pdf"
            path = os.path.join(account_dir, filename)
            txs = [tx for tx in all_period_txs if tx["created_at"][:7] == period]
            opening = running_balance
            credits = Decimal("0.00")
            debits = Decimal("0.00")
            fees = Decimal("0.00")
            for tx in txs:
                delta = signed_amount(tx)
                if delta >= 0:
                    credits += delta
                else:
                    debits += -delta
                if tx["from_account"] == acc["account_number"]:
                    fees += Decimal(str(tx["fee"] or 0))
                running_balance += delta
            closing = running_balance
            c = canvas.Canvas(path, pagesize=letter)
            c.drawString(72, 730, "Super Insecure Bank")
            c.drawString(72, 708, f"Monthly Account Statement: {period}")
            c.drawString(72, 686, f"Owner: {acc['full_name']}")
            c.drawString(72, 664, f"Account: {acc['account_number']} ({acc['account_type']})")
            c.drawString(72, 642, f"Opening balance: {opening:.2f} USD")
            c.drawString(72, 622, f"Credits: {credits:.2f} USD   Debits: {debits:.2f} USD   Fees: {fees:.2f} USD")
            c.drawString(72, 602, f"Closing balance: {closing:.2f} USD")
            y = 570
            c.drawString(72, y, "Transactions:")
            y -= 20
            for tx in txs:
                sign = "+" if tx["to_account"] == acc["account_number"] else "-"
                display_amount = Decimal(str(tx["amount"]))
                line = f"{tx['created_at'][:10]} {tx['transfer_id']} {tx['from_account']}->{tx['to_account']} {sign}{display_amount:.2f} fee {Decimal(str(tx['fee'] or 0)):.2f} {tx['description']}"
                c.drawString(72, y, line[:95])
                y -= 16
                if y < 80:
                    c.showPage()
                    y = 730
            c.save()
    conn.close()


@app.after_request
def weak_headers(response):
    # Deliberately weak/missing hardening headers for the lab.
    return response


@app.route("/")
def welcome():
    return render_template("welcome.html")


@app.route("/login", methods=["GET"])
def login():
    if current_user():
        return redirect(url_for("accounts"))
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data, error = require_json_body(["username", "password"])
    if error:
        return error
    username = data.get("username", "")
    password = data.get("password", "")
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if user and user["password_hash"] == md5(password):
        token = make_access_token(user)
        log_event(f"LOGIN_SUCCESS user={username} jwt={token}")
        resp = jsonify({
            "message": "Login successful",
            "authenticated": True,
            "redirect": url_for("accounts"),
            "user": {"username": user["username"], "full_name": user["full_name"]}
        })
        resp.set_cookie("access_token", token, httponly=True, samesite="Lax", path="/")
        return resp
    log_event(f"LOGIN_FAILED user={username} password={password}")
    return jsonify({"error": "Invalid username or password", "authenticated": False}), 200


@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("login")))
    resp.delete_cookie("access_token", path="/")
    return resp


@app.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("accounts"))


@app.route("/accounts")
@login_required
def accounts():
    # Page shell only. Account header data is loaded by JavaScript from /api/accounts.
    return render_template("accounts.html")


@app.route("/api/accounts")
@login_required
def api_accounts():
    user = current_user()
    conn = db()
    accounts = conn.execute("SELECT account_number, account_type, currency, balance FROM accounts WHERE username=? ORDER BY account_number", (user["username"],)).fetchall()
    conn.close()
    return jsonify({
        "customer": {
            "name": user["full_name"],
            "username": user["username"]
        },
        "accounts": [{
            "account_number": a["account_number"],
            "account_type": a["account_type"],
            "currency": a["currency"],
            "balance": f"{a['balance']:.2f}"
        } for a in accounts]
    })


@app.route("/api/accounts/<account_id>/transactions")
@login_required
def account_transactions_json(account_id):
    # A10: this is the same real data endpoint used by the View details button.
    # Supplying a non-numeric account id causes a verbose technical error.
    if not str(account_id).isdigit():
        query = f"SELECT * FROM transactions WHERE from_account={account_id} OR to_account={account_id}"
        stacktrace = f"""ValueError: invalid account identifier: '{account_id}'

Traceback:
  File "/app/routes/accounts.py", line 91, in account_transactions_json
    account_id = int(account_id)
  File "/app/services/transaction_service.py", line 37, in load_transactions
    query = "SELECT * FROM transactions WHERE from_account = " + account_id
  File "/app/db.py", line 31, in execute_query
    cursor.execute(query)
"""
        return jsonify({
            "error": "Invalid account identifier",
            "account_id": account_id,
            "stacktrace": stacktrace,
            "query": query,
            "database": f"sqlite:///{DB_PATH}"
        }), 500

    conn = db()
    # A01 BOLA: the normal UI only lists the authenticated user's accounts via /api/accounts,
    # but this data endpoint intentionally does not enforce ownership when an account id is supplied manually.
    account = conn.execute("""
        SELECT a.*, u.username AS owner_username, u.full_name AS owner_name
        FROM accounts a
        JOIN users u ON u.username = a.username
        WHERE a.account_number=?
    """, (account_id,)).fetchone()
    if not account:
        conn.close()
        return jsonify({"error": "Account not found"}), 404
    search = request.args.get("search", "").strip()
    # A05.1 SQL Injection: deliberately vulnerable string concatenation for the account transaction search.
    sql = f"SELECT * FROM transactions WHERE (from_account='{account_id}' OR to_account='{account_id}')"
    if search:
        sql += f" AND description LIKE '%{search}%'"
    sql += " ORDER BY created_at DESC, id DESC LIMIT 30"
    try:
        rows = conn.execute(sql).fetchall()
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e), "query": sql}), 500
    conn.close()
    txs = []
    for t in rows:
        incoming = t["to_account"] == account_id
        txs.append({
            "id": t["transfer_id"],
            "from_account": t["from_account"],
            "to_account": t["to_account"],
            "amount": f"{t['amount']:.2f}",
            "signed_amount": ("+" if incoming else "-") + f"{t['amount']:.2f}",
            "fee": f"{t['fee']:.2f}",
            "currency": t["currency"],
            "description": t["description"],
            "created_at": t["created_at"],
            "receipt_id": f"R-{t['transfer_id']}"
        })
    return jsonify({
        "account": {
            "account_number": account["account_number"],
            "account_type": account["account_type"],
            "currency": account["currency"],
            "balance": f"{account['balance']:.2f}",
            "owner_username": account["owner_username"],
            "owner_name": account["owner_name"]
        },
        "transactions": txs
    })

@app.route("/accounts/<account_id>")
@login_required
def account_detail(account_id):
    # The account detail UI was retired to avoid mixed HTML/data behavior.
    # Use /accounts for the page shell and /api/accounts/<account_id>/transactions for JSON data.
    return redirect(url_for("accounts"))

@app.route("/profile", methods=["GET"])
@login_required
def profile():
    return render_template("profile.html")


@app.route("/api/customer-profile")
@login_required
def api_customer_profile():
    user = current_user()
    return jsonify({
        "full_name": user["full_name"],
        "email": user["email"],
        "username": user["username"],
        "otp_phone": user["otp_phone"],
        "address": user["address"],
        "occupation": user["occupation"],
        "monthly_income": user["monthly_income"],
        "source_of_funds": user["source_of_funds"]
    })


@app.route("/api/profile/kyc/update", methods=["POST"])
@login_required
def profile_kyc_update():
    user = current_user()
    data, error = require_json_body(["address", "occupation", "monthly_income", "source_of_funds"])
    if error:
        return error
    # A01 BOPLA / mass assignment: all received fields are applied, including otp_phone.
    allowed_columns = ["address", "occupation", "monthly_income", "source_of_funds", "otp_phone"]
    updates = []
    values = []
    updated_fields = {}
    for k, v in data.items():
        if k in allowed_columns:
            updates.append(f"{k}=?")
            values.append(v)
            updated_fields[k] = v
    conn = db()
    if updates:
        values.append(user["username"])
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE username=?", values)
        conn.commit()
    updated = conn.execute("SELECT * FROM users WHERE username=?", (user["username"],)).fetchone()
    conn.close()
    return jsonify({
        "message": "Customer profile updated successfully.",
        "updated_fields": updated_fields,
        "profile": {
            "username": updated["username"],
            "address": updated["address"],
            "occupation": updated["occupation"],
            "monthly_income": updated["monthly_income"],
            "source_of_funds": updated["source_of_funds"],
            "otp_phone": updated["otp_phone"]
        }
    })


@app.route("/loans")
@login_required
def loans():
    return render_template("loans.html")


@app.route("/api/loans/applications")
@login_required
def loans_applications():
    user = current_user()
    conn = db()
    rows = conn.execute("SELECT * FROM loans WHERE username=? ORDER BY id DESC", (user["username"],)).fetchall()
    conn.close()
    return jsonify({
        "applications": [{
            "id": r["loan_id"] or f"L{r['id']:04d}",
            "account_id": r["account_id"],
            "amount": f"{Decimal(str(r['amount'] or '0')):.2f}",
            "currency": r["currency"] or "USD",
            "term_months": int(r["term_months"] or 0),
            "purpose": r["purpose"] or "Personal expenses",
            "status": r["status"],
            "created_at": r["created_at"]
        } for r in rows]
    })


@app.route("/api/loans/apply", methods=["POST"])
@login_required
def loans_apply():
    user = current_user()
    data, error = require_json_body(["account_id", "amount", "term_months", "purpose"])
    if error:
        return error
    account_id = data.get("account_id")
    amount = data.get("amount")
    term_months = data.get("term_months")
    purpose = data.get("purpose")
    currency = "USD"
    # A01 BFLA: backend does not check loan_enabled / branch validation,
    # but the selected account must still belong to the authenticated user.
    conn = db()
    owned = conn.execute("SELECT account_number FROM accounts WHERE account_number=? AND username=?", (account_id, user["username"])).fetchone()
    if not owned:
        conn.close()
        return jsonify({"error": "Invalid account"}), 403
    last = conn.execute("SELECT id FROM loans ORDER BY id DESC LIMIT 1").fetchone()
    next_id = (int(last["id"]) + 1) if last else 1
    loan_id = f"L{9000 + next_id}"
    created_at = datetime.now().replace(microsecond=0).isoformat()
    conn.execute("INSERT INTO loans(username, account_id, amount, term_months, purpose, currency, loan_id, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                 (user["username"], account_id, amount, term_months, purpose, currency, loan_id, "PRE_APPROVED", created_at))
    conn.commit()
    conn.close()
    return jsonify({
        "message": "Loan application submitted successfully",
        "loan": {
            "id": loan_id,
            "account_id": account_id,
            "amount": f"{Decimal(str(amount)):.2f}",
            "currency": currency,
            "term_months": int(term_months),
            "purpose": purpose,
            "status": "PRE_APPROVED",
            "created_at": created_at
        }
    })


@app.route("/transactions")
@login_required
def transactions():
    return redirect(url_for("accounts"))


@app.route("/transfers", methods=["GET"])
@login_required
def transfers():
    return render_template("transfer.html")


def fee_for_transfer(conn, from_account, to_account, amount):
    from_user = conn.execute("SELECT username FROM accounts WHERE account_number=?", (from_account,)).fetchone()
    to_user = conn.execute("SELECT username FROM accounts WHERE account_number=?", (to_account,)).fetchone()
    if not from_user or not to_user or from_user["username"] == to_user["username"]:
        return Decimal("0.00")
    raw = Decimal(str(amount)) * Decimal("0.01")
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@app.route("/api/transfers/create", methods=["POST"])
@login_required
def transfer_create():
    data, error = require_json_body(["from_account", "to_account", "amount"])
    if error:
        return error
    from_account = data.get("from_account")
    to_account = data.get("to_account")
    note = (data.get("note") or "").strip()
    try:
        amount = Decimal(str(data.get("amount", "0")))
    except Exception:
        return jsonify({"error": "Invalid amount"}), 400
    conn = db()
    fee = fee_for_transfer(conn, from_account, to_account, amount)
    total = amount + fee
    src = conn.execute("SELECT * FROM accounts WHERE account_number=?", (from_account,)).fetchone()
    dst = conn.execute("SELECT * FROM accounts WHERE account_number=?", (to_account,)).fetchone()
    user = current_user()
    if not src or not dst:
        conn.close()
        return jsonify({"error": "Invalid account"}), 400
    if src["username"] != user["username"]:
        conn.close()
        return jsonify({"error": "Source account is not available for this user"}), 403
    if Decimal(str(src["balance"])) < total:
        conn.close()
        return jsonify({"error": "Insufficient funds"}), 400
    last = conn.execute("SELECT transfer_id FROM transactions WHERE transfer_id LIKE 'T%' ORDER BY CAST(substr(transfer_id,2) AS INTEGER) DESC LIMIT 1").fetchone()
    next_id = (int(last["transfer_id"][1:]) + 1) if last else 9001
    transfer_id = f"T{next_id}"
    created_at = datetime.now().replace(microsecond=0).isoformat()
    # Currency is intentionally inferred by the backend from the USD account model; the client request does not send currency.
    currency = "USD"
    conn.execute("UPDATE accounts SET balance = balance - ? WHERE account_number=?", (float(total), from_account))
    conn.execute("UPDATE accounts SET balance = balance + ? WHERE account_number=?", (float(amount), to_account))
    description = note or "Online transfer"
    conn.execute("INSERT INTO transactions(transfer_id,from_account,to_account,amount,fee,currency,description,status,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                 (transfer_id, from_account, to_account, float(amount), float(fee), currency, description, "APPROVED", created_at))
    conn.commit()
    conn.close()
    return jsonify({
        "message": "Transfer completed successfully",
        "transfer": {
            "id": transfer_id,
            "from_account": from_account,
            "to_account": to_account,
            "amount": f"{amount:.2f}",
            "fee": f"{fee:.2f}",
            "total_debit": f"{total:.2f}",
            "currency": currency,
            "status": "APPROVED",
            "created_at": created_at,
            "payment_reference": description
        }
    })



@app.route("/receipts")
@login_required
def receipts():
    return render_template("receipts.html")


@app.route("/api/receipts")
@login_required
def api_receipts():
    user = current_user()
    conn = db()
    user_accounts = [r["account_number"] for r in conn.execute("SELECT account_number FROM accounts WHERE username=?", (user["username"],)).fetchall()]
    if user_accounts:
        placeholders = ",".join(["?"] * len(user_accounts))
        rows = conn.execute(f"SELECT * FROM receipts WHERE from_account IN ({placeholders}) OR to_account IN ({placeholders}) ORDER BY created_at DESC, id DESC", (*user_accounts, *user_accounts)).fetchall()
    else:
        rows = []
    conn.close()
    return jsonify({
        "receipts": [{
            "receipt_id": r["receipt_id"],
            "transfer_id": r["transfer_id"],
            "from_account": r["from_account"],
            "to_account": r["to_account"],
            "amount": r["amount"],
            "currency": r["currency"],
            "status": r["status"],
            "created_at": r["created_at"],
            "payment_reference": r["payment_reference"]
        } for r in rows]
    })

@app.route("/api/receipts/generate", methods=["POST"])
@login_required
def receipts_generate():
    data, error = require_json_body(["transfer_id", "from_account", "to_account", "amount", "currency", "status"])
    if error:
        return error
    transfer_id = data.get("transfer_id")
    receipt_id = f"R-{transfer_id}"
    conn = db()
    # A08: trusts client-supplied receipt fields.
    created_at = datetime.now().isoformat()
    payment_reference = data.get("payment_reference")
    conn.execute("INSERT OR REPLACE INTO receipts(receipt_id,transfer_id,from_account,to_account,amount,currency,status,created_at,payment_reference) VALUES (?,?,?,?,?,?,?,?,?)",
                 (receipt_id, transfer_id, data.get("from_account"), data.get("to_account"), data.get("amount"), data.get("currency", "USD"), data.get("status", "APPROVED"), created_at, payment_reference))
    transfer = conn.execute("SELECT amount, currency, description FROM transactions WHERE transfer_id=?", (transfer_id,)).fetchone()
    conn.commit()
    conn.close()
    original_amount = f"{float(transfer['amount']):.2f}" if transfer else str(data.get("amount"))
    original_currency = transfer["currency"] if transfer else data.get("currency", "USD")
    return jsonify({
        "message": "Receipt generated successfully",
        "receipt": {
            "receipt_id": receipt_id,
            "transfer_id": transfer_id,
            "from_account": data.get("from_account"),
            "to_account": data.get("to_account"),
            "amount": str(data.get("amount")),
            "currency": data.get("currency", "USD"),
            "status": data.get("status", "APPROVED"),
            "created_at": created_at,
            "payment_reference": payment_reference or (transfer["description"] if transfer else None)
        },
        "original_transfer_amount": original_amount,
        "original_transfer_currency": original_currency
    })


@app.route("/receipts/<receipt_id>")
@login_required
def receipt_view(receipt_id):
    user = current_user()
    conn = db()
    receipt = conn.execute("SELECT * FROM receipts WHERE receipt_id=?", (receipt_id,)).fetchone()
    transfer = None
    if receipt:
        user_accounts = [r["account_number"] for r in conn.execute("SELECT account_number FROM accounts WHERE username=?", (user["username"],)).fetchall()]
        if receipt["from_account"] not in user_accounts and receipt["to_account"] not in user_accounts:
            conn.close()
            return render_template("receipt.html", receipt=None, transfer=None, error="Receipt not found"), 404
        transfer = conn.execute("SELECT * FROM transactions WHERE transfer_id=?", (receipt["transfer_id"],)).fetchone()
    conn.close()
    if not receipt:
        return render_template("receipt.html", receipt=None, transfer=None, error="Receipt not found"), 404
    return render_template("receipt.html", receipt=receipt, transfer=transfer)


@app.route("/statements")
@login_required
def statements():
    return render_template("statements.html")


@app.route("/api/statements/accounts/<path:account_id>")
@login_required
def api_statements_for_account(account_id):
    # A05.2 command injection: the selected account id is concatenated into a shell command
    # used to list statement PDFs. Normal and exploited responses are JSON; injected
    # command output contaminates the files[] array as if it were part of the listing.
    import re
    user = current_user()
    base_account = re.split(r"[;&|`$]", account_id, 1)[0].strip()
    conn = db()
    owned = conn.execute("SELECT account_number FROM accounts WHERE account_number=? AND username=?", (base_account, user["username"])).fetchone()
    conn.close()
    if not owned:
        return jsonify({"error": "Account not found"}), 404

    cmd = f"ls {os.path.join(STATEMENTS_DIR, account_id)}"
    try:
        raw = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        output = raw.decode("utf-8", errors="ignore")
    except subprocess.CalledProcessError as e:
        output = e.output.decode("utf-8", errors="ignore")

    lines = [x.strip() for x in output.splitlines() if x.strip()]
    if any(ch in account_id for ch in [";", "&", "|", "`", "$("]):
        files = lines
    else:
        files = [x for x in lines if x.endswith(".pdf")]
    return jsonify({"files": files})


@app.route("/statements/download")
@login_required
def statements_download():
    filename = request.args.get("filename", "")
    base = os.path.abspath(STATEMENTS_DIR)
    target = os.path.abspath(os.path.join(STATEMENTS_DIR, filename))
    account_folder = filename.split("/", 1)[0] if "/" in filename else ""
    user = current_user()
    conn = db()
    owned = conn.execute("SELECT account_number FROM accounts WHERE account_number=? AND username=?", (account_folder, user["username"])).fetchone()
    conn.close()
    if not owned or not target.startswith(base) or not os.path.exists(target):
        return "Statement not found", 404
    return send_file(target, mimetype="application/pdf", as_attachment=True, download_name=os.path.basename(target))


@app.route("/forgot-password", methods=["GET"])
def forgot_password():
    return render_template("forgot_password.html")


@app.route("/api/forgot-password", methods=["POST"])
def api_forgot_password():
    data, error = require_json_body(["username"])
    if error:
        return error
    username = data.get("username", "")
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if user:
        token = make_reset_token(username)
        conn.execute("INSERT INTO reset_tokens(token,username,created_at) VALUES (?,?,?)", (token, username, datetime.now().isoformat()))
        reset_url = f"{request.host_url.rstrip('/')}/reset-password?token={token}"
        body = reset_url
        conn.execute("INSERT INTO mails(username,subject,body,created_at) VALUES (?,?,?,?)", (username, "Password Reset", body, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"message": "If the username exists, a password reset link has been generated. Please check your mailbox."})
    conn.close()
    return jsonify({"error": "No account was found with that username."}), 404


@app.route("/reset-password", methods=["GET"])
def reset_password():
    # HTML shell only. Token context is loaded by /api/reset-password/context.
    return render_template("reset_password.html")


@app.route("/api/reset-password/context")
def api_reset_password_context():
    token = request.args.get("token", "")
    payload = decode_reset_token(token)
    if not payload:
        return jsonify({"valid": False, "error": "Invalid reset token"}), 400
    return jsonify({"valid": True, "username": payload.get("username", "")})


@app.route("/api/reset-password/confirm", methods=["POST"])
def reset_password_confirm():
    data, error = require_json_body(["token", "username", "new_password"])
    if error:
        return error
    token = data.get("token")
    username = data.get("username")
    new_password = data.get("new_password")
    conn = db()
    reset_payload = decode_reset_token(token)
    token_row = conn.execute("SELECT * FROM reset_tokens WHERE token=?", (token,)).fetchone()
    # A07: validates reset JWT exists and is signed, but does not verify token subject matches submitted username.
    if reset_payload and token_row and username and new_password:
        conn.execute("UPDATE users SET password_hash=? WHERE username=?", (md5(new_password), username))
        conn.commit()
        conn.close()
        return jsonify({"message": "Password changed successfully", "username": username})
    conn.close()
    return jsonify({"error": "Invalid token or request"}), 400


@app.route("/mailbox")
def mailbox():
    username = request.args.get("username", "")
    return render_template("mailbox.html", username=username)


@app.route("/api/mailbox")
def api_mailbox():
    username = request.args.get("username", "")
    conn = db()
    mails = conn.execute("SELECT * FROM mails WHERE username=? ORDER BY id DESC", (username,)).fetchall()
    conn.close()
    return jsonify({
        "username": username,
        "messages": [{
            "subject": m["subject"],
            "created_at": m["created_at"],
            "body": m["body"],
            "is_password_reset": m["subject"] == "Password Reset"
        } for m in mails]
    })


@app.route("/social")
def social():
    comments = [
        ("Fernando Conislla", "I still do not understand why my balance changed after my last transfer."),
        ("Alice Morrison", "I lost access to my account twice this month."),
        ("Bob Wilson", "The password reset process feels unsafe."),
        ("Carla Bennett", "My statement shows a transaction I never made."),
        ("Daniel Brooks", "Support told me everything was normal, but my balance was different."),
        ("Laura Mendez", "I tried to open an account, but the app looks suspicious."),
        ("Kevin Adams", "I do not trust a bank that exposes so much information."),
        ("Sofia Ramirez", "This bank needs better security before I register."),
        ("Natalie Foster", "The login page feels broken."),
        ("Michael Torres", "I saw people complaining about missing funds here."),
    ]
    return render_template("social.html", comments=comments)


@app.route("/security-dashboard")
def security_dashboard():
    return render_template("security_dashboard.html")


@app.route("/api/security-logs")
def api_security_logs():
    path = os.path.join(DATA_DIR, "security.log")
    logs = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            logs = [line.rstrip("\n") for line in f]
    logs.reverse()
    return jsonify({"logs": logs})


@app.route("/api/security-logs/clear", methods=["POST"])
def api_security_logs_clear():
    path = os.path.join(DATA_DIR, "security.log")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("")
    return jsonify({"message": "Security log cleared successfully"})


@app.route("/status")
def exposed_status():
    return jsonify({
        "hostname": "sib-web-01",
        "environment": "development",
        "debug": True,
        "database": DB_PATH,
        "log_path": os.path.join(DATA_DIR, "security.log"),
        "server": "Werkzeug/2.2.2",
        "python": "3.10.12",
        "werkzeug_debugger": "enabled",
        "internal_paths": ["/app/app.py", "/app/data/statements", DB_PATH],
        "warning": "Status endpoint exposed without authentication"
    })


@app.route("/console")
def console():
    return make_response("""
    <html><head><title>Werkzeug Debugger Console</title></head>
    <body style="font-family: monospace; padding: 40px;">
      <h1>Werkzeug Debugger Console</h1>
      <p>Console locked</p>
      <p>The console is locked and needs to be unlocked by entering the PIN.</p>
      <form><input placeholder="PIN"><button>Unlock</button></form>
    </body></html>
    """)


@app.route("/api/profile")
def api_profile():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
    else:
        token = request.cookies.get("access_token", "")
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        return jsonify({"error": str(e) or "missing token"}), 401
    username = data.get("username") or data.get("sub")
    conn = db()
    user = conn.execute("SELECT username,email,full_name FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if not user:
        return jsonify({"error": "user not found"}), 401
    return jsonify({"username": user["username"], "email": user["email"], "full_name": user["full_name"], "role": data.get("role")})




if __name__ == "__main__":
    init_db()
    from werkzeug.serving import make_server
    server = make_server("0.0.0.0", 5000, app)
    server.serve_forever()
else:
    init_db()
