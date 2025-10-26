from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_FILE = "car_booking.db"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------
# Initialize DB
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            car_model TEXT,
            pickup_date TEXT,
            total_bill REAL,
            status TEXT,
            duration TEXT,
            toll_charge REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def calculate_rent(duration, toll):
    base = 1500 if duration == "12" else 2500
    return base + toll


# ---------------------------------------------------------
# Login
# ---------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


# ---------------------------------------------------------
# Signup
# ---------------------------------------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect('/login')
        except:
            conn.close()
            return render_template('signup.html', error="Username already exists")

    return render_template('signup.html')


# ---------------------------------------------------------
# Booking / Add Trip
# ---------------------------------------------------------
@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        duration = request.form.get('duration')
        toll_charge = float(request.form.get('toll_charge', 0))

        rent = calculate_rent(duration, toll_charge)
        customer_name = f"{first_name} {last_name}".strip()

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO bookings (customer_name, car_model, pickup_date, total_bill, status, duration, toll_charge)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (customer_name, "Toyota Innova", datetime.now().strftime("%Y-%m-%d %I:%M %p"), rent, "Pending Approval", duration, toll_charge))
        conn.commit()
        conn.close()

        # Save for verify page
        session['user_info'] = {
            'first_name': first_name,
            'last_name': last_name,
            'aadhar_no': request.form.get('aadhar_no', 'N/A'),
            'license_no': request.form.get('license_no', 'N/A')
        }

        return redirect('/verify')

    return render_template('booking.html')


# ---------------------------------------------------------
# Verification Page
# ---------------------------------------------------------
@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        action = request.form.get('action')

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        if action == 'approve':
            status = "Confirmed"
        elif action == 'reupload':
            status = "Reupload Requested"
        elif action == 'cancel':
            status = "Cancelled"
        else:
            status = "Pending Approval"

        cur.execute("UPDATE bookings SET status=? WHERE id=(SELECT MAX(id) FROM bookings)", (status,))
        conn.commit()
        conn.close()

        return redirect('/dashboard')

    # ✅ FIX: Provide user info to template
    user_info = session.get('user_info', {
        'first_name': 'Unknown',
        'last_name': '',
        'aadhar_no': 'N/A',
        'license_no': 'N/A'
    })

    return render_template('verify.html', user=user_info)


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, customer_name, car_model, pickup_date, total_bill, status FROM bookings ORDER BY id DESC")
    bookings = cur.fetchall()
    conn.close()

    # Dynamic Stats (no default data)
    total_bookings = len(bookings)
    total_revenue = sum(b[4] for b in bookings) if bookings else 0
    pending = sum(1 for b in bookings if b[5] == "Pending Approval")
    confirmed = sum(1 for b in bookings if b[5] == "Confirmed")

    stats = {
        "pickups": confirmed,
        "returns": 0,
        "pending": pending,
        "revenue": f"₹ {total_revenue:,.0f}"
    }

    return render_template('dashboard.html', bookings=bookings, stats=stats)


# ---------------------------------------------------------
# Logout
# ---------------------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
