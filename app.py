import os
import tempfile
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# Handle SQLite DB path for local development vs Vercel serverless environment
if os.environ.get('VERCEL'):
    db_path = os.path.join(tempfile.gettempdir(), 'registrations.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///registrations.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'super_secret_secure_key'

db = SQLAlchemy(app)

# ==== MODELS ====

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    registrations = db.relationship('Registration', backref='event', lazy=True, cascade="all, delete-orphan")

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15))
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Ensure DB tables are created on initialization
def init_db():
    with app.app_context():
        db.create_all()
        if not Event.query.first():
            demo_event = Event(
                name="Tech Innovation Summit 2026",
                description="Join us for the largest tech gathering of the year on our college campus. Industry leaders and top students will showcase new technologies.",
                date="May 15th, 2026",
                location="Main Auditorium"
            )
            db.session.add(demo_event)
            db.session.commit()

init_db()

# ==== ADMIN AUTH DECORATOR ====

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==== USER ROUTES ====

@app.route('/')
def index():
    events = Event.query.all()
    return render_template('index.html', events=events)

@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        new_reg = Registration(
            full_name=request.form['full_name'],
            email=request.form['email'],
            phone=request.form.get('phone', ''),
            event_id=event.id
        )
        db.session.add(new_reg)
        db.session.commit()
        return redirect(url_for('success', name=new_reg.full_name, event=event.name))
    return render_template('register.html', event=event)

@app.route('/success')
def success():
    name = request.args.get('name')
    event = request.args.get('event')
    return render_template('success.html', name=name, event=event)

# ==== ADMIN ROUTES ====

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == 'admin@college.edu' and password == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('admin_events'))
        else:
            flash('Invalid email or password.')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin/events')
@login_required
def admin_events():
    events = Event.query.all()
    return render_template('admin_events.html', events=events)

@app.route('/admin/events/new', methods=['GET', 'POST'])
@login_required
def admin_events_new():
    if request.method == 'POST':
        new_event = Event(
            name=request.form['name'],
            description=request.form['description'],
            date=request.form['date'],
            location=request.form['location']
        )
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('admin_events'))
    return render_template('admin_event_form.html', event=None)

@app.route('/admin/events/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
def admin_events_edit(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        event.name = request.form['name']
        event.description = request.form['description']
        event.date = request.form['date']
        event.location = request.form['location']
        db.session.commit()
        return redirect(url_for('admin_events'))
    return render_template('admin_event_form.html', event=event)

@app.route('/admin/events/delete/<int:event_id>', methods=['POST'])
@login_required
def admin_events_delete(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for('admin_events'))

@app.route('/admin/registrations')
@login_required
def registrations():
    all_regs = Registration.query.order_by(Registration.created_at.desc()).all()
    return render_template('registrations.html', registrations=all_regs)

# ==== STARTUP SCRIPTS ====

if __name__ == '__main__':
    app.run(debug=True, port=5000)
