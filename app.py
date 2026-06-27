from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import random

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this_later'

# --- CONFIG ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iara_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='Fisherman')
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
    status = db.Column(db.String(20), default='Active')


# НОВО: Модел за глобите
class Fine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inspector_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    offender_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_issued = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


with app.app_context():
    db.create_all()


# --- ROUTES ---
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
            session['role'] = user.role
            return redirect(url_for('dashboard'))

        flash('Invalid username or password')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    if User.query.filter_by(username=username).first():
        flash('Username already exists!')
        return redirect(url_for('login'))

    new_user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role='Fisherman'
    )

    db.session.add(new_user)
    db.session.commit()

    session['user_id'] = new_user.id
    session['username'] = new_user.username
    session['role'] = new_user.role

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/ticket')
def ticket():
    if 'user_id' not in session:
        flash('Please log in to purchase a fishing permit.')
        return redirect(url_for('login'))

    return render_template('ticket.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to view your dashboard.')
        return redirect(url_for('login'))

    user_tickets = (
        Ticket.query
        .filter_by(user_id=session['user_id'])
        .order_by(Ticket.purchase_date.desc())
        .all()
    )

    return render_template('dashboard.html', tickets=user_tickets)


# --- API ---
@app.route('/calculate', methods=['POST'])
def calculate_price():
    payload = request.get_json(silent=True) or {}

    age_group = payload.get('age', 'adult')
    duration = payload.get('duration', 'day')
    is_disabled = bool(payload.get('disabled', False))

    if is_disabled:
        return jsonify({'price': 0.0})

    base_prices = {
        'day': 5.0,
        'week': 15.0,
        'year': 40.0,
    }

    price = base_prices.get(duration, 5.0)

    if age_group in {'child', 'pensioner'}:
        price *= 0.5

    return jsonify({'price': round(price, 2)})


@app.route('/buy', methods=['POST'])
def buy_ticket():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or {}

    try:
        price = float(payload.get('price', 0))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Invalid price'}), 400

    permit_id = f"IARA-{random.randint(100000, 999999)}"
    while Ticket.query.filter_by(permit_id=permit_id).first():
        permit_id = f"IARA-{random.randint(100000, 999999)}"

    new_ticket = Ticket(
        user_id=session['user_id'],
        permit_id=permit_id,
        price=round(price, 2),
        purchase_date=datetime.now(timezone.utc)
    )

    db.session.add(new_ticket)
    db.session.commit()

    return jsonify({
        'status': 'ok',
        'ticket_id': permit_id,
        'price': round(price, 2)
    })


# --- INSPECTOR ---
@app.route('/inspector', methods=['GET', 'POST'])
def inspector_dashboard():
    if session.get('role') != 'Inspector':
        flash('Access Denied: Official IARA Inspectors only.')
        return redirect(url_for('dashboard'))

    search_result = None
    searched = False

    if request.method == 'POST':
        # Проверяваме дали това е формата за търсене (има permit_id)
        if 'permit_id' in request.form:
            searched = True
            search_query = request.form.get('permit_id', '').strip()
            search_result = Ticket.query.filter_by(permit_id=search_query).first()

    return render_template('inspector.html', ticket=search_result, searched=searched)


# НОВО: Маршрут за издаване на глоби
@app.route('/issue_fine', methods=['POST'])
def issue_fine():
    if session.get('role') != 'Inspector':
        flash('Access Denied: Only Inspectors can issue fines.')
        return redirect(url_for('dashboard'))

    offender_name = request.form.get('offender_name', '').strip()
    description = request.form.get('description', '').strip()
    amount_val = request.form.get('amount', '0')

    if offender_name and description:
        new_fine = Fine(
            inspector_id=session['user_id'],
            offender_name=offender_name,
            description=description,
            amount=float(amount_val)
        )
        db.session.add(new_fine)
        db.session.commit()
        flash(f'Penalty of {amount_val} € successfully issued to {offender_name}!')

    return redirect(url_for('inspector_dashboard'))


# --- VESSELS ---
@app.route('/vessels')
def vessels():
    if 'user_id' not in session:
        flash('Please log in to manage vessels.')
        return redirect(url_for('login'))

    all_vessels = Vessel.query.order_by(Vessel.id.desc()).all()
    return render_template('vessels.html', vessels=all_vessels)


@app.route('/register_vessel', methods=['POST'])
def register_vessel():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    name = request.form.get('name', '').strip()
    reg_num = request.form.get('reg_num', '').strip()
    tonnage_val = request.form.get('tonnage', '0')
    power_val = request.form.get('power', '0')

    if not name or not reg_num:
        flash('Vessel name and registration number are required.')
        return redirect(url_for('vessels'))

    if Vessel.query.filter_by(registration_number=reg_num).first():
        flash('A vessel with this registration number already exists.')
        return redirect(url_for('vessels'))

    new_vessel = Vessel(
        user_id=session['user_id'],
        name=name,
        registration_number=reg_num,
        tonnage=float(tonnage_val),
        engine_power=float(power_val)
    )

    db.session.add(new_vessel)
    db.session.commit()

    flash('Vessel registered successfully.')
    return redirect(url_for('vessels'))


if __name__ == '__main__':
    app.run(debug=True)