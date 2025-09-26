from database import db
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # hashed passwords are long
    role = db.Column(db.String(20), nullable=False)  # Admin / Doctor / Patient
    doctor_profile = db.relationship('Doctor', backref='user', uselist=False)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    specialization = db.Column(db.String(50), nullable=False)
    available_days = db.Column(db.String(100), nullable=False)  # e.g., "Mon,Tue,Wed"
    available_slots = db.Column(db.String(200), nullable=True)  # e.g., "09:00,10:00,11:00"
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)

    def get_slots(self):
        if self.available_slots:
            return [slot.strip() for slot in self.available_slots.split(',')]
        return []
    
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    appointments = db.relationship('Appointment', backref='patient', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    problem = db.Column(db.String(300), nullable=True)
    status = db.Column(db.String(50))  # Booked / Completed / Cancelled
    remarks = db.Column(db.Text, nullable=True) 
    rating = db.Column(db.Integer, nullable=True)
    treatment = db.relationship('Treatment', backref='appointment', uselist=False)

class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    disease = db.Column(db.Text, nullable=False)
    diagnosis = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
