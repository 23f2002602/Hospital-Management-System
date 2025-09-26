from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, DateField, TimeField, TextAreaField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange

class LoginForm(FlaskForm):
    email = StringField('Email', validators = [DataRequired(), Email()])
    password = PasswordField('Password', validators = [DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="passwords must match")])
    role = SelectField('Role', choices=[('Patient', 'Patient'), ('Doctor', 'Doctor')], validators=[DataRequired()])
    submit = SubmitField('Register')

class DoctorSetupForm(FlaskForm):
    specialization = StringField('Specialization', validators=[DataRequired()])
    available_days = SelectMultipleField(
        "Available Days",
        choices=[
            ("Mon", "Monday"), ("Tue", "Tuesday"), ("Wed", "Wednesday"),
            ("Thu", "Thursday"), ("Fri", "Friday"), ("Sat", "Saturday"), ("Sun", "Sunday")
        ],
        validators=[DataRequired()]
    )
    available_slots = StringField('Available Slots (comma separated, e.g., 09:00,10:00,11:00)', validators=[DataRequired()])
    submit = SubmitField('Add/Update Doctor')

class AppointmentForm(FlaskForm):
    doctor_id = SelectField('Doctor', coerce=int)
    patient_id = SelectField('Patient', coerce=int)
    date = DateField('Date', validators=[DataRequired()])
    time = SelectField('Time', coerce=str)  # dynamic slots
    problem = StringField('Problem', validators=[DataRequired()])
    submit = SubmitField('Book Appointment')

    def __init__(self, available_slots=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if available_slots:
            self.time.choices = [(slot, slot) for slot in available_slots]
        else:
            self.time.choices = []

class TreatmentForm(FlaskForm):
    diagnosis = TextAreaField('Diagnosis', validators=[DataRequired()])
    prescription = TextAreaField('Prescription')
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Treatment')

class FeedbackForm(FlaskForm):
    remarks = TextAreaField('Remarks')
    rating = IntegerField('Rating (1-5)', validators=[NumberRange(min=1, max=5)])
    submit = SubmitField('Submit Feedback')