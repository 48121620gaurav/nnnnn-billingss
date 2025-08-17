from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
from pymongo import MongoClient
import os, uuid
from pymongo.errors import ConnectionFailure

# ---------------------- MongoDB Atlas Connection ----------------------
MONGO_URI = "mongodb+srv://gauravmishra21604:mahadev1234@cluster0.mrtcqps.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(MONGO_URI, tls=True)
    client.admin.command('ping')
    print("✅ Connected to MongoDB Atlas successfully!")

    # Database and collections
    db = client["maadurgaji"]
    users_col = db["users"]
    licenses_col = db["licenses"]

except ConnectionFailure as e:
    print("❌ Could not connect to MongoDB:", e)
except Exception as e:
    print("⚠️ Error:", e)

# ---------------------- Flask App Init ----------------------
app = Flask(__name__)
app.secret_key = 'demo-secret'

# ---------------------- API LOGIN ----------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password required"}), 400

    license = licenses_col.find_one({"email": email, "password": password})
    if license:
        valid_until = datetime.strptime(license["valid_until"], "%Y-%m-%d").date()
        today = datetime.now().date()

        if not license["is_active"] or today > valid_until:
            return jsonify({"message": "License expired"}), 403

        return jsonify({"message": "Login successful", "client_id": license["client_id"]}), 200

    return jsonify({"message": "Invalid credentials"}), 401

# ---------------------- ROUTES ----------------------
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        if users_col.find_one({"email": email}):
            flash("Email already exists!", "danger")
            return redirect(url_for('signup'))

        user = {
            "name": request.form['name'],
            "mobile": request.form['mobile'],
            "email": email,
            "password": request.form['password'],
            "amount": request.form['amount'],
            "signup_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        users_col.insert_one(user)
        flash("Signup successful!", "success")
        return redirect(url_for('welcome'))

    return render_template('signup.html')

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/admin')
def admin_dashboard():
    licenses = []
    today = datetime.today()

    for lic in licenses_col.find():
        try:
            valid_until = datetime.strptime(lic["valid_until"], "%Y-%m-%d")
            status = "Valid" if lic["is_active"] and today <= valid_until else "Expired"
        except ValueError:
            status = "Invalid Date"

        licenses.append({
            "client_id": lic["client_id"],
            "client_name": lic["client_name"],
            "email": lic["email"],
            "machine_id": lic["machine_id"],
            "last_payment": lic["last_payment"],
            "valid_until": lic["valid_until"],
            "status": status
        })

    return render_template("dashboard.html", licenses=licenses)

@app.route('/activate', methods=["GET", "POST"])
def activate():
    if request.method == "POST":
        client_name = request.form.get('client_name')
        email = request.form.get('email')
        client_id = request.form.get('client_id')
        transaction_id = request.form.get('transaction_id')
        duration = int(request.form.get('duration'))
        password = request.form.get('password')

        today = datetime.today()
        valid_until = today + timedelta(days=duration)
        machine_id = str(uuid.uuid4())

        duplicate = licenses_col.find_one({"email": email, "client_id": client_id})
        if duplicate:
            return render_template("activate.html", already_activated=True)

        license = {
            "client_name": client_name,
            "email": email,
            "client_id": client_id,
            "transaction_id": transaction_id,
            "duration": duration,
            "machine_id": machine_id,
            "password": password,
            "last_payment": today.strftime("%Y-%m-%d"),
            "valid_until": valid_until.strftime("%Y-%m-%d"),
            "is_active": True
        }
        licenses_col.insert_one(license)
        flash(f"✅ License activated for {client_name}.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("activate.html", already_activated=False)

@app.route('/deactivate/<client_id>')
def deactivate(client_id):
    licenses_col.update_one({"client_id": client_id}, {"$set": {"is_active": False}})
    flash(f"Client {client_id} deactivated.", "warning")
    return redirect(url_for("admin_dashboard"))

@app.route('/activate/<client_id>')
def reactivate(client_id):
    today = datetime.today()
    valid_until = today + timedelta(days=30)

    licenses_col.update_one(
        {"client_id": client_id},
        {"$set": {
            "is_active": True,
            "last_payment": today.strftime("%Y-%m-%d"),
            "valid_until": valid_until.strftime("%Y-%m-%d")
        }}
    )
    flash(f"Client {client_id} reactivated for 30 days.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('home'))

# ✅ Corrected entry point
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
