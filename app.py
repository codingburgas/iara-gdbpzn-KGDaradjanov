from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
import random
import csv
from io import StringIO
from flask import Response
from reportlab.pdfgen import canvas
from io import BytesIO
import requests
import os
from dotenv import load_dotenv

load_dotenv()


def get_weather():
    api_key = os.getenv("WEATHER_API_KEY")
    city = "Burgas"
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return {
            "temp": round(data["main"]["temp"]),
            "desc": data["weather"][0]["description"]
        }
    except Exception as e:
        print("Weather Error:", e)
        return None


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
    catch_logs = db.relationship('CatchLog', backref='owner', lazy=True)


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

    captain_name = db.Column(db.String(100), nullable=False)
    length = db.Column(db.Float, nullable=False)
    width = db.Column(db.Float, nullable=False)
    draft = db.Column(db.Float, nullable=False)
    fuel_type = db.Column(db.String(50), nullable=False)
    international_number = db.Column(db.String(50))

    status = db.Column(db.String(20), default='Active')
    permit = db.relationship('CommercialPermit', backref='vessel', uselist=False, cascade="all, delete-orphan")
    catch_logs = db.relationship('CatchLog', backref='vessel', lazy=True)


class CommercialPermit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vessel_id = db.Column(db.Integer, db.ForeignKey('vessel.id'), unique=True, nullable=False)
    permit_number = db.Column(db.String(20), unique=True, nullable=False)
    issue_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expiry_date = db.Column(db.DateTime, nullable=False)  # time that is valid
    is_revoked = db.Column(db.Boolean, default=False)  # revoke permit


class Fine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inspector_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    offender_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_issued = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class CatchLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vessel_id = db.Column(db.Integer, db.ForeignKey('vessel.id'), nullable=True)
    catch_date = db.Column(db.String(20), nullable=False)
    gear_used = db.Column(db.String(50), nullable=False)
    fish_species = db.Column(db.String(50), nullable=False)
    quantity_kg = db.Column(db.Float, nullable=False)
    lot_number = db.Column(db.String(20), unique=True, nullable=False)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)


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
        flash('Моля влезте в профила си, за да купите билет.')
        return redirect(url_for('login'))
    return render_template('ticket.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_tickets = Ticket.query.filter_by(user_id=user_id).order_by(Ticket.purchase_date.desc()).all()

    logs = CatchLog.query.filter_by(user_id=user_id).all()
    catch_data = {}
    for log in logs:
        species = log.fish_species.capitalize()
        catch_data[species] = catch_data.get(species, 0) + log.quantity_kg

    return render_template('dashboard.html', tickets=user_tickets, catch_data=catch_data)


@app.route('/calculate', methods=['POST'])
def calculate_price():
    payload = request.get_json(silent=True) or {}
    age_group = payload.get('age', 'adult')
    duration = payload.get('duration', 'day')
    is_disabled = bool(payload.get('disabled', False))
    if is_disabled:
        return jsonify({'price': 0.0})
    base_prices = {'day': 5.0, 'week': 15.0, 'year': 40.0}
    price = base_prices.get(duration, 5.0)
    if age_group in {'child', 'pensioner'}:
        price *= 0.5
    return jsonify({'price': round(price, 2)})


@app.route('/buy', methods=['POST'])
def buy_ticket():
    if 'user_id' not in session:
        return jsonify({'status': 'error'}), 401
    payload = request.get_json(silent=True) or {}
    try:
        price = float(payload.get('price', 0))
    except (TypeError, ValueError):
        return jsonify({'status': 'error'}), 400
    permit_id = f"IARA-{random.randint(100000, 999999)}"
    new_ticket = Ticket(
        user_id=session['user_id'],
        permit_id=permit_id,
        price=round(price, 2),
        purchase_date=datetime.now(timezone.utc)
    )
    db.session.add(new_ticket)
    db.session.commit()
    return jsonify({'status': 'ok', 'ticket_id': permit_id, 'price': round(price, 2)})


@app.route('/inspector', methods=['GET', 'POST'])
def inspector_dashboard():
    if session.get('role') != 'Inspector':
        return redirect(url_for('dashboard'))
    search_result = None
    searched = False
    if request.method == 'POST':
        searched = True
        search_query = request.form.get('permit_id', '').strip()
        search_result = Ticket.query.filter_by(permit_id=search_query).first()
    return render_template('inspector.html', ticket=search_result, searched=searched)


@app.route('/issue_fine', methods=['POST'])
def issue_fine():
    if session.get('role') != 'Inspector':
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
        flash(f'Глоба от {amount_val} € е издадена на {offender_name}!')
    return redirect(url_for('inspector_dashboard'))


@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'Admin':
        return redirect(url_for('dashboard'))
    all_users = User.query.all()
    total_users = User.query.count()
    total_vessels = Vessel.query.count()
    total_fines = db.session.query(db.func.sum(Fine.amount)).scalar() or 0.0
    total_catch = db.session.query(db.func.sum(CatchLog.quantity_kg)).scalar() or 0.0
    return render_template('admin.html', users=all_users, total_users=total_users,
                           total_vessels=total_vessels, total_fines=round(total_fines, 2),
                           total_catch=round(total_catch, 2))


@app.route('/change_role', methods=['POST'])
def change_role():
    if session.get('role') != 'Admin':
        return redirect(url_for('dashboard'))
    user_id = request.form.get('user_id')
    new_role = request.form.get('new_role')
    user = db.session.get(User, user_id)
    if user and new_role in ['Fisherman', 'Inspector', 'Admin']:
        user.role = new_role
        db.session.commit()
        if user.id == session.get('user_id'):
            session['role'] = new_role
    return redirect(url_for('admin_dashboard'))


@app.route('/logbook', methods=['GET', 'POST'])
def logbook():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_vessels = Vessel.query.filter_by(user_id=session['user_id']).all()

    if request.method == 'POST':
        vessel_id = request.form.get('vessel_id')
        catch_date = request.form.get('catch_date')
        gear = request.form.get('gear')
        species = request.form.get('species')
        qty = request.form.get('quantity')

        v_id = None
        if not vessel_id:
            user_tickets = Ticket.query.filter_by(user_id=session['user_id']).all()
            if not user_tickets:
                flash('Трябва ви активен риболовен билет, за да регистрирате любителски улов!', 'error')
                return redirect(url_for('logbook'))
        else:
            v_id = int(vessel_id)

        try:
            qty_float = float(qty)
        except ValueError:
            return redirect(url_for("logbook"))

        protected_species = ['есетра', 'делфин', 'морска котка', 'тюлен']
        if species.lower() in protected_species:
            flash(f'🚨 АЛАРМА: Уловът на {species.capitalize()} е забранен!', 'error')
            return redirect(url_for('logbook'))

        lot_num = f"LOT-{random.randint(1000000, 9999999)}"
        new_log = CatchLog(
            user_id=session['user_id'],
            vessel_id=v_id,
            catch_date=catch_date,
            gear_used=gear,
            fish_species=species,
            quantity_kg=qty_float,
            lot_number=lot_num,
            lat=request.form.get('lat'),
            lon=request.form.get('lon')
        )
        db.session.add(new_log)
        db.session.commit()
        flash(f'Уловът е записан! Партиден номер: {lot_num}')
        return redirect(url_for('logbook'))

    logs = CatchLog.query.filter_by(user_id=session['user_id']).order_by(CatchLog.id.desc()).all()
    return render_template('logbook.html', vessels=user_vessels, logs=logs)


@app.route('/trace', methods=['GET', 'POST'])
def trace():
    search_result = None
    vessel = None
    searched = False
    if request.method == 'POST':
        searched = True
        lot_query = request.form.get('lot_number', '').strip()
        search_result = CatchLog.query.filter_by(lot_number=lot_query).first()
        if search_result and search_result.vessel_id:
            vessel = Vessel.query.get(search_result.vessel_id)
    return render_template('trace.html', log=search_result, vessel=vessel, searched=searched)


@app.route('/vessels', methods=['GET'])
def vessels():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    search_query = request.args.get('search', '').strip()
    weather = get_weather()

    if search_query:
        all_vessels = Vessel.query.filter(
            (Vessel.name.ilike(f'%{search_query}%')) | (Vessel.registration_number.ilike(f'%{search_query}%'))
        ).order_by(Vessel.id.desc()).all()
    else:
        all_vessels = Vessel.query.order_by(Vessel.id.desc()).all()

    return render_template('vessels.html', vessels=all_vessels, search_query=search_query, weather=weather)


@app.route('/register_vessel', methods=['POST'])
def register_vessel():
    if 'user_id' not in session: return redirect(url_for('login'))

    name = request.form.get('name', '').strip()
    reg_num = request.form.get('reg_num', '').strip()

    new_vessel = Vessel(
        user_id=session['user_id'],
        name=name,
        registration_number=reg_num,
        captain_name=request.form.get('captain_name', ''),
        international_number=request.form.get('international_number', ''),
        tonnage=float(request.form.get('tonnage', '0')),
        engine_power=float(request.form.get('power', '0')),
        fuel_type=request.form.get('fuel_type', ''),
        length=float(request.form.get('length', '0')),
        width=float(request.form.get('width', '0')),
        draft=float(request.form.get('draft', '0'))
    )
    db.session.add(new_vessel)
    db.session.commit()
    flash('Корабът е регистриран успешно.')
    return redirect(url_for('vessels'))


@app.route('/issue_commercial_permit/<int:vessel_id>', methods=['POST'])
def issue_commercial_permit(vessel_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    vessel = Vessel.query.get_or_404(vessel_id)
    if vessel.user_id != session['user_id']: return redirect(url_for('vessels'))

    permit_num = f"COM-{random.randint(10000, 99999)}"
    new_permit = CommercialPermit(
        vessel_id=vessel.id,
        permit_number=permit_num,
        expiry_date=datetime.now(timezone.utc) + timedelta(days=365)
    )
    db.session.add(new_permit)
    db.session.commit()
    flash(f'Стопанско разрешително {permit_num} е издадено!')
    return redirect(url_for('vessels'))


@app.route('/revoke_permit/<int:permit_id>', methods=['POST'])
def revoke_permit(permit_id):
    if session.get('role') not in ['Inspector', 'Admin']:
        flash('Достъп отказан: Само инспектори могат да отнемат разрешителни.')
        return redirect(url_for('vessels'))

    permit = CommercialPermit.query.get_or_404(permit_id)
    permit.is_revoked = True
    db.session.commit()
    flash(f'Разрешително {permit.permit_number} беше отнето поради нарушение!')
    return redirect(url_for('vessels'))


@app.route('/export_pdf')
def export_pdf():
    if 'user_id' not in session: return redirect(url_for('login'))
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "IARA OFFICIAL CATCH REPORT")
    y = 750
    for log in CatchLog.query.filter_by(user_id=session['user_id']).all():
        p.drawString(100, y, f"Species: {log.fish_species} | Qty: {log.quantity_kg}kg | Date: {log.catch_date}")
        y -= 20
        if y < 50:
            p.showPage()
            y = 800
    p.showPage()
    p.save()
    pdf_out = buffer.getvalue()
    buffer.close()
    return Response(pdf_out, mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment; filename=report.pdf'})


@app.route('/export_vessels')
def export_vessels():
    if 'user_id' not in session: return redirect(url_for('login'))

    def generate():
        data = StringIO()
        writer = csv.writer(data)
        writer.writerow(['ID', 'Vessel Name', 'Reg Number', 'Tonnage', 'Power', 'Permit'])
        yield data.getvalue()
        data.seek(0);
        data.truncate(0)
        for v in Vessel.query.all():
            permit_num = v.permit.permit_number if (v.permit and not v.permit.is_revoked) else "No Permit"
            writer.writerow([v.id, v.name, v.registration_number, v.tonnage, v.engine_power, permit_num])
            yield data.getvalue()
            data.seek(0);
            data.truncate(0)

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment; filename=vessels.csv"})


if __name__ == '__main__':
    app.run()