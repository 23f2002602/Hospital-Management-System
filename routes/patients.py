from flask import jsonify
from routes.routes import *
from models import *
from forms import FeedbackForm, PatientSetupForm, AppointmentForm
from datetime import datetime, date
patient_bp = Blueprint('patient', __name__)

## PATIENT DASHBOARD ##

@patient_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'Patient' :
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
    
    patient = current_user.patient_profile
    today = date.today()

    age = today.year - patient.dob.year - ((today.month, today.day) < (patient.dob.month, patient.dob.day))

    future_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.date >= today
        ).order_by(Appointment.date, Appointment.time).all()
    
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.date < today
        ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    
    return render_template('patient/dashboard.html', patient=patient, 
                           age=age, 
                           upcoming_appointments=future_appointments, 
                           past_appointments=past_appointments)

@patient_bp.route('/profile.edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = PatientSetupForm()
    user = current_user
    patient_profile = user.patient_profile

    if form.validate_on_submit():
        user.name = form.name.data
        patient_profile.dob = form.dob.data
        patient_profile.phone_number = form.phone_number.data
        
        db.session.commit()

        flash('Profile updated successfully.', 'success')
        return redirect(url_for('patient.dashboard'))
    
    elif request.method == 'GET':
        form.name.data = user.name
        form.dob.data = patient_profile.dob
        form.phone_number.data = patient_profile.phone_number

    return render_template('patient/patient_forms.html', 
                           form=form, 
                           title="Edit Profile",
                           form_type='edit_profile')

## PATIENT APPOINTMENT MANAGEMENT ##

@patient_bp.route('/appointment/edit/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def edit_appt(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    if appt.patient_id != current_user.patient_profile.id:
        abort(403)
    
    if appt.date < date.today():
        flash('Past appointments cannot be edited.', 'warning')
        return redirect(url_for('patient.dashboard'))

    if appt.status != AppointmentStatus.BOOKED:
        flash(f'This appointment cannot be edited as it is already {appt.status.value}.', 'warning')
        return redirect(url_for('patient.dashboard'))
    
    form = AppointmentForm()
    doctors = Doctor.query.join(User).all()

    form.doctor_id.choices = [(doc.id, f"Dr. {doc.user.name} - {doc.specialization}") for doc in doctors]
    
    if form.validate_on_submit():
        appt.doctor_id = form.doctor_id.data
        appt.date = form.date.data
        appt.time = form.time.data
        appt.problem = form.problem.data

        db.session.commit()
        flash('Appointment updated successfully.', 'success')
        return redirect(url_for('patient.dashboard'))
    
    elif request.method == 'GET':
        form.doctor_id.data = appt.doctor_id
        form.date.data = appt.date
        form.time.data = appt.time.strftime('%H:%M')
        form.problem.data = appt.problem

    return render_template('patient/patient_forms.html', form=form, appointment=appt, form_type='edit_appt')

@patient_bp.route('/appointment/delete/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    if appt.patient_id != current_user.patient_profile.id:
        abort(403)

    db.session.delete(appt)
    db.session.commit()
    flash('Appointment has been deleted successfully.', 'success')
    return redirect(url_for('patient.dashboard'))

@patient_bp.route('/appointment/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appt(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    if appt.patient_id != current_user.patient_profile.id:
        abort(403)

    if appt.date < date.today():
        flash('Past appointments cannot be cancelled.', 'warning')
        return redirect(url_for('patient.dashboard'))

    if appt.status != AppointmentStatus.BOOKED:
        flash(f'This appointment cannot be cancelled as it is already {appt.status.value}.', 'warning')
        return redirect(url_for('patient.dashboard'))

    appt.status = AppointmentStatus.CANCELLED
    db.session.commit()
    flash('Appointment has been cancelled successfully.', 'success')
    return redirect(url_for('patient.dashboard'))

@patient_bp.route('/feedback/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def feedback(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    form = FeedbackForm()

    if appt.patient_id != current_user.patient_profile.id:
        abort(403)

    if appt.status != AppointmentStatus.COMPLETED:
        flash('Feedback can only be given for completed appointments.', 'warning')
        return redirect(url_for('patient.dashboard'))

    if appt.rating and appt.remarks:
        flash('Feedback has already been submitted for this appointment.', 'info')
        return redirect(url_for('patient.dashboard'))

    if form.validate_on_submit():
        appt.remarks = form.remarks.data
        appt.rating = form.rating.data

        db.session.commit()

        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('patient.dashboard'))
    
    return render_template('patient/patient_forms.html', form=form, appointment=appt)

## APPOINTMENT BOOKING ##

@patient_bp.route('/appointment/book', methods=['GET', 'POST'])
@login_required
def book_appt():
    form = AppointmentForm()

    doctors = Doctor.query.join(User).all()
    form.doctor_id.choices = [(doc.id, f"Dr. {doc.user.name} - {doc.specialization}") for doc in doctors]

    if form.validate_on_submit():
        appointment_time = datetime.strptime(form.time.data, '%H:%M').time()

        new_appointment = Appointment(
            patient_id = current_user.patient_profile.id,
            doctor_id = form.doctor_id.data,
            date = form.date.data,
            time = appointment_time,
            problem = form.problem.data,
            status = AppointmentStatus.BOOKED
        )

        db.session.add(new_appointment)
        db.session.commit()

        flash('Appointment booked successfully.', 'success')
        return redirect(url_for('patient.dashboard'))
    
    return render_template('patient/Appt_booking.html', form=form)

@patient_bp.route('/doctors')
@login_required
def list_doctors():
    doctors = Doctor.query.join(User).all()
    availability_by_doctor = {}

    for doctor in doctors:
        availability = DoctorAvailability.query.filter_by(doctor_id=doctor.id).all()
        availability_by_doctor[doctor.id] = {
            'days': sorted(list(set([avail.day.value for avail in availability]))),
            'slots': sorted(list(set([avail.start_time.strftime('%H:%M') for avail in availability])))
        }

    return render_template('patient/list_doctors.html', doctors=doctors, availability_by_doctor=availability_by_doctor)

@patient_bp.route('/get-slots/<int:doctor_id>/<string:date_str>')
@login_required
def get_slots(doctor_id, date_str):
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_of_week = selected_date.strftime('%A').upper()

        available_slots = DoctorAvailability.query.filter_by(
            doctor_id=doctor_id,
            day=DayOfWeek[day_of_week]
        ).all()

        slots = [slot.start_time.strftime('%H:%M') for slot in available_slots]
        return jsonify(slots)

    except (ValueError, KeyError):
        return jsonify([])