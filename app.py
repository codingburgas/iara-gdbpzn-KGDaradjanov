from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import random

app = Flask(__name__)

# Secret key
app.secret_key = 'super_secret_key_change_this_later'

# DB config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iara_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    tickets = db.relationship('Ticket', backref='owner', lazy=True)


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permit_id = db.Column(db.String(20), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Vessel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(20), unique=True, nullable=False)
    tonnage = db.Column(db.Float, nullable=False)
    engine_power = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Active")


# Create tables
with app.app_context():
    db.create_all()


# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/ticket')
def ticket():
    return render_template('ticket.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    existing_user = User.query.filter_by(username=username).first()

    if existing_user:
        flash('Username already exists!')
        return redirect(url_for('login'))

    hashed_password = generate_password_hash(password)

    new_user = User(username=username, password_hash=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    session['user_id'] = new_user.id
    session['username'] = new_user.username

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to view your dashboard.')
        return redirect(url_for('login'))

    user_tickets = Ticket.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', tickets=user_tickets)


# ---------------- VESSELS ----------------
@app.route('/vessels')
def vessels():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    all_vessels = Vessel.query.all()
    return render_template('vessels.html', vessels=all_vessels)


@app.route('/register_vessel', methods=['POST'])
def register_vessel():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    name = request.form.get('name', '')
    reg_num = request.form.get('reg_num', '')
    tonnage_val = request.form.get('tonnage', '0')
    power_val = request.form.get('power', '0')

    new_vessel = Vessel(
        user_id=session['user_id'],
        name=name,
        registration_number=reg_num,
        tonnage=float(tonnage_val),
        engine_power=float(power_val)
    )

    db.session.add(new_vessel)
    db.session.commit()

    return jsonify({'status': 'success'})


# ---------------- START APP ----------------
if __name__ == "__main__":
    app.run(debug=True)