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
        Appointment.date >= today,
        Appointment.status == AppointmentStatus.BOOKED,
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

        # Load slots for the current appointment
        if appt.doctor_id and appt.date:
            available_slots = get_available_slots(appt.doctor_id, appt.date)
            current_time_str = appt.time.strftime('%H:%M')
            if current_time_str not in available_slots:
                available_slots.append(current_time_str)
            if available_slots:
                form.time.choices = [(slot, slot) for slot in sorted(available_slots)]

    return render_template('patient/patient_forms.html', form=form, appointment=appt, form_type='edit_appt')

@patient_bp.route('/appointment/delete/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    if appt.patient_id != current_user.patient_profile.id:
        abort(403)
    
    # Only allow deleting upcoming appointments (not past appointments)
    if appt.date < date.today():
        flash('Cannot delete past appointments.', 'warning')
        return redirect(url_for('patient.dashboard'))
    
    # Only allow deleting booked appointments
    if appt.status != AppointmentStatus.BOOKED:
        flash(f'Cannot delete appointment with status {appt.status.value}.', 'warning')
        return redirect(url_for('patient.dashboard'))

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
    # Check if user is a patient
    if current_user.role != 'Patient':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
    
    # Check if patient profile exists
    if not current_user.patient_profile:
        flash('Patient profile not found. Please complete your profile first.', 'danger')
        return redirect(url_for('patient.dashboard'))
    
    form = AppointmentForm()

    doctors = Doctor.query.join(User).all()
    if not doctors:
        flash('No doctors available. Please contact administrator.', 'warning')
        return redirect(url_for('patient.dashboard'))
    
    form.doctor_id.choices = [(doc.id, f"Dr. {doc.user.name} - {doc.specialization}") for doc in doctors]

    # Populate available slots based on selected doctor and date
    load_slots_requested = request.form.get('load_slots') is not None
    
    # Process form data to get doctor_id and date
    doctor_id = None
    selected_date = None
    
    if request.method == 'POST':
        # Process form data - need to manually process since validation might fail
        # Get doctor_id from form or raw request
        if request.form.get('doctor_id'):
            try:
                doctor_id = int(request.form.get('doctor_id'))
                form.doctor_id.data = doctor_id
            except (ValueError, TypeError):
                pass
        
        # Get date from form or raw request  
        date_input = request.form.get('date')
        if date_input:
            try:
                if isinstance(date_input, str):
                    selected_date = datetime.strptime(date_input, '%Y-%m-%d').date()
                else:
                    selected_date = date_input
                form.date.data = selected_date
            except (ValueError, TypeError):
                pass
        
        # Preserve problem field if it was filled
        if request.form.get('problem'):
            form.problem.data = request.form.get('problem')
    
    elif request.method == 'GET':
        # Check if doctor_id and date are provided as query parameters
        doctor_id = request.args.get('doctor_id', type=int)
        date_str = request.args.get('date')
        
        if doctor_id and date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                # Pre-populate form
                form.doctor_id.data = doctor_id
                form.date.data = selected_date
            except ValueError:
                pass
    
    # Always populate slots if doctor and date are available (before validation)
    available_slots = []
    final_doctor_id = doctor_id or form.doctor_id.data
    final_date = selected_date or form.date.data
    
    if final_doctor_id and final_date:
        available_slots = get_available_slots(final_doctor_id, final_date)
        
        # Update form time choices with available slots
        if available_slots:
            form.time.choices = [(slot, slot) for slot in sorted(available_slots)]
        else:
            form.time.choices = [('', 'No available slots for this date')]
    else:
        # Update form time choices - show placeholder if no doctor/date selected
        form.time.choices = [('', 'Please select doctor and date first')]

    # If user clicked "Load Available Slots" or changed doctor/date (but not submitting), don't validate the form, just show slots
    submit_clicked = request.form.get('submit') is not None
    if (load_slots_requested or (request.method == 'POST' and not submit_clicked)) and not form.validate_on_submit():
        if not final_doctor_id or not final_date:
            flash('Please select both a doctor and a date to load available slots.', 'info')
        elif not available_slots:
            flash('No available slots found for the selected doctor and date.', 'warning')
        else:
            flash(f'Found {len(available_slots)} available slot(s) for the selected date.', 'success')
        return render_template('patient/Appt_booking.html', form=form, title="Booking New Appointment")

    if form.validate_on_submit():
        if not form.time.data or form.time.data == '':
            flash('Please select a time slot.', 'danger')
            # Re-populate slots for re-rendering
            if form.doctor_id.data and form.date.data:
                available_slots = get_available_slots(form.doctor_id.data, form.date.data)
                form.time.choices = [(slot, slot) for slot in sorted(available_slots)] if available_slots else []
            return render_template('patient/Appt_booking.html', form=form, title="Booking New Appointment")
        
        try:
            appointment_time = datetime.strptime(form.time.data, '%H:%M').time()
        except ValueError:
            flash('Invalid time format. Please select a valid time slot.', 'danger')
            # Re-populate slots for re-rendering
            if form.doctor_id.data and form.date.data:
                available_slots = get_available_slots(form.doctor_id.data, form.date.data)
                form.time.choices = [(slot, slot) for slot in sorted(available_slots)] if available_slots else []
            return render_template('patient/Appt_booking.html', form=form, title="Booking New Appointment")

        # Check if the slot is still available (prevent double-booking)
        existing_appointment = Appointment.query.filter_by(
            doctor_id=form.doctor_id.data,
            date=form.date.data,
            time=appointment_time,
            status=AppointmentStatus.BOOKED
        ).first()

        if existing_appointment:
            flash('This time slot is already booked. Please select another time.', 'danger')
            # Re-populate slots for re-rendering
            if form.doctor_id.data and form.date.data:
                available_slots = get_available_slots(form.doctor_id.data, form.date.data)
                form.time.choices = [(slot, slot) for slot in sorted(available_slots)] if available_slots else []
            return render_template('patient/Appt_booking.html', form=form, title="Booking New Appointment")

        # Validate that the date is not in the past
        if form.date.data < date.today():
            flash('Cannot book appointments in the past. Please select a future date.', 'danger')
            # Re-populate slots for re-rendering
            if form.doctor_id.data and form.date.data:
                available_slots = get_available_slots(form.doctor_id.data, form.date.data)
                form.time.choices = [(slot, slot) for slot in sorted(available_slots)] if available_slots else []
            return render_template('patient/Appt_booking.html', form=form, title="Booking New Appointment")

        # Check if patient profile exists
        if not current_user.patient_profile:
            flash('Patient profile not found. Please contact administrator.', 'danger')
            return redirect(url_for('patient.dashboard'))
        
        new_appointment = Appointment(
            patient_id = current_user.patient_profile.id,
            doctor_id = form.doctor_id.data,
            date = form.date.data,
            time = appointment_time,
            problem = form.problem.data,
            status = AppointmentStatus.BOOKED
        )

        try:
            db.session.add(new_appointment)
            db.session.commit()
            flash('Appointment booked successfully.', 'success')
            return redirect(url_for('patient.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while booking the appointment. Please try again.', 'danger')
            # Re-populate slots for re-rendering
            if form.doctor_id.data and form.date.data:
                available_slots = get_available_slots(form.doctor_id.data, form.date.data)
                form.time.choices = [(slot, slot) for slot in sorted(available_slots)] if available_slots else []
            return render_template('patient/Appt_booking.html', form=form, title="Booking New Appointment")
    
    return render_template('patient/Appt_booking.html', form=form, title="Booking New Appointment")

def get_available_slots(doctor_id, selected_date):
    """Helper function to get available slots for a doctor on a given date"""
    try:
        day_of_week = selected_date.strftime('%A').upper()

        # Get all available slots for the doctor on this day of week
        available_slots = DoctorAvailability.query.filter_by(
            doctor_id=doctor_id,
            day=DayOfWeek[day_of_week]
        ).all()

        # Get all already booked appointments for this doctor on this date
        booked_appointments = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=selected_date,
            status=AppointmentStatus.BOOKED
        ).all()

        # Extract booked times as strings
        booked_times = {appt.time.strftime('%H:%M') for appt in booked_appointments}

        # Filter out booked slots
        available_times = [
            slot.start_time.strftime('%H:%M') 
            for slot in available_slots 
            if slot.start_time.strftime('%H:%M') not in booked_times
        ]

        return available_times
    except (ValueError, KeyError):
        return []

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

        # Get all available slots for the doctor on this day of week
        available_slots = DoctorAvailability.query.filter_by(
            doctor_id=doctor_id,
            day=DayOfWeek[day_of_week]
        ).all()

        # Get all already booked appointments for this doctor on this date
        booked_appointments = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=selected_date,
            status=AppointmentStatus.BOOKED
        ).all()

        # Extract booked times as strings
        booked_times = {appt.time.strftime('%H:%M') for appt in booked_appointments}

        # Filter out booked slots
        available_times = [
            slot.start_time.strftime('%H:%M') 
            for slot in available_slots 
            if slot.start_time.strftime('%H:%M') not in booked_times
        ]

        return jsonify(available_times)

    except (ValueError, KeyError) as e:
        return jsonify([])