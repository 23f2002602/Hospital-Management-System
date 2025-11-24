import enum
from database import db
from flask_login import UserMixin

class AppointmentStatus(enum.Enum):
    BOOKED = "Booked"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class DayOfWeek(enum.Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # hashed passwords are long
    role = db.Column(db.String(20), nullable=False)  # Admin / Doctor / Patient
    doctor_profile = db.relationship('Doctor', backref='user', uselist=False)
    patient_profile = db.relationship('Patient', backref='user', uselist=False)

class DoctorAvailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    day = db.Column(db.Enum(DayOfWeek), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    # Ensures a doctor can't have overlapping slots on the same day
    __table_args__ = (db.UniqueConstraint('doctor_id', 'day', 'start_time', name='_doctor_day_start_uc'),)


class DoctorAvailabilityOverride(db.Model):
    """
    Per-date overrides for a doctor's availability. This allows a doctor to enable/disable
    specific slots for a particular calendar date without changing their weekly schedule.
    """
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    # When True this slot is explicitly available on that date even if not part of weekly schedule.
    # When False this slot is explicitly blocked on that date even if part of weekly schedule.
    is_available = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (db.UniqueConstraint('doctor_id', 'date', 'start_time', name='_doctor_date_start_uc'),)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    specialization = db.Column(db.String(50), nullable=False)
    availability = db.relationship('DoctorAvailability', backref='doctor', lazy='dynamic', cascade="all, delete-orphan")
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)

    def get_slots(self):
        if self.available_slots:
            return [slot.strip() for slot in self.available_slots.split(',')]
        return []
    
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
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
    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)
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
