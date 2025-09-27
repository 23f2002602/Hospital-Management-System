from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, DateField, TimeField, TextAreaField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange
from wtforms import widgets

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
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False),
    )
    available_slots = SelectMultipleField(
        "Available Slots",
        choices=[
            ("09:00", "09:00"), ("09:30", "09:30"),
            ("10:00", "10:00"), ("10:30", "10:30"),
            ("11:00", "11:00"), ("11:30", "11:30"),
            ("12:00", "12:00"), ("12:30", "12:30"),
            ("13:00", "13:00"), ("13:30", "13:30"),
            ("14:00", "14:00"), ("14:30", "14:30"),
            ("15:00", "15:00"), ("15:30", "15:30"),
            ("16:00", "16:00"), ("16:30", "16:30"),
            ("17:00", "17:00"), ("17:30", "17:30"),
            ("18:00", "18:00"), ("18:30", "18:30"),
            ("19:00", "19:00"), ("19:30", "19:30"),
            ("20:00", "20:00"), ("20:30", "20:30"),
            ("21:00", "21:00"), ("21:30", "21:30"),
            ("22:00", "22:00"), ("22:30", "22:30")
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False),
    )
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