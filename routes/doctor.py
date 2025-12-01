from routes.routes import *
from models import *
from forms import TreatmentForm, DoctorProfileForm, DailySlotForm
from datetime import date
from datetime import datetime, timedelta
from collections import defaultdict

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'Doctor':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    doctor = current_user.doctor_profile
    # allow selecting a date via query param ?date=YYYY-MM-DD
    qdate = request.args.get('date')
    try:
        selected_date = datetime.strptime(qdate, '%Y-%m-%d').date() if qdate else date.today()
    except Exception:
        selected_date = date.today()
    today = date.today()

    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.date >= today,
        Appointment.status == AppointmentStatus.BOOKED
    ).order_by(Appointment.date, Appointment.time).all()
    
    completed_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == AppointmentStatus.COMPLETED
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()

    # Build per-day slot view for the selected date (shows booked/free)
    slots_display = []
    day_enum = get_weekday_enum_for_date(selected_date)
    weekly_slots = build_slots_from_availability(doctor, day_enum)
    overrides = { (o.start_time.strftime('%H:%M')): o for o in DoctorAvailabilityOverride.query.filter_by(doctor_id=doctor.id, date=selected_date).all() }
    appts_on_day = Appointment.query.filter_by(doctor_id=doctor.id, date=selected_date, status=AppointmentStatus.BOOKED).all()
    booked_times = { a.time.strftime('%H:%M') for a in appts_on_day }

    seen = set()
    for st, et, label in weekly_slots:
        seen.add(label)
        override = overrides.get(label)
        is_available = True if override is None else override.is_available
        is_booked = label in booked_times
        slots_display.append({'time': label, 'is_weekly': True, 'override': override, 'is_available': is_available, 'is_booked': is_booked})
    for label, o in overrides.items():
        if label not in seen:
            is_booked = label in booked_times
            slots_display.append({'time': label, 'is_weekly': False, 'override': o, 'is_available': o.is_available, 'is_booked': is_booked})
    slots_display.sort(key=lambda x: datetime.strptime(x['time'], '%H:%M').time())

    return render_template(
        'doctor/dashboard.html', 
        doctor=doctor, 
        upcoming_appointments=upcoming_appointments,
        completed_appointments=completed_appointments
        , selected_date=selected_date, slots_display=slots_display
    )


@doctor_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if current_user.role != 'Doctor':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    doctor = current_user.doctor_profile
    form = DoctorProfileForm(obj=doctor)

    if form.validate_on_submit():
        try:
            doctor.specialization = form.specialization.data
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('doctor.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {e}', 'danger')

    if request.method == 'GET':
        form.specialization.data = doctor.specialization

    return render_template('doctor/profile_edit.html', form=form, doctor=doctor)


def get_weekday_enum_for_date(dt):
    return DayOfWeek[dt.strftime('%A').upper()]


def build_slots_from_availability(doctor, day_enum):
    """Return list of tuples (start_time_obj, end_time_obj, str_label) for the weekly availability for given day."""
    slots = []
    avails = DoctorAvailability.query.filter_by(doctor_id=doctor.id, day=day_enum).order_by(DoctorAvailability.start_time).all()
    for a in avails:
        slots.append((a.start_time, a.end_time, a.start_time.strftime('%H:%M')))
    return slots


@doctor_bp.route('/slots', methods=['GET', 'POST'])
@login_required
def manage_slots():
    """Manage slots for a selected date. Shows which slots are booked/free and allows toggling availability overrides."""
    if current_user.role != 'Doctor':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    doctor = current_user.doctor_profile
    form = DailySlotForm()

    selected_date = None
    slots_display = []  # each item: {time, is_weekly, override, is_booked}

    if form.validate_on_submit():
        # Save overrides: Clear existing overrides for this date and create new ones based on comparison
        selected_date = form.date.data
        
        # 1. Get standard weekly slots for this day
        day_enum = get_weekday_enum_for_date(selected_date)
        weekly_slots_objs = build_slots_from_availability(doctor, day_enum)
        weekly_times = set(s[2] for s in weekly_slots_objs) # s[2] is the string label 'HH:MM'
        
        # 2. Get slots selected in the form
        selected_slots = set(form.slots.data or [])
        
        # 3. Identify slots to BLOCK (Present in weekly, but unchecked in form)
        to_block = weekly_times - selected_slots
        
        # 4. Identify slots to ADD (Not in weekly, but checked in form)
        to_add = selected_slots - weekly_times
        
        # delete existing overrides for that date to start fresh
        DoctorAvailabilityOverride.query.filter_by(doctor_id=doctor.id, date=selected_date).delete()
        
        # Create BLOCKING overrides (is_available=False)
        for slot_str in to_block:
            st = datetime.strptime(slot_str, '%H:%M').time()
            et = (datetime.combine(datetime.today(), st) + timedelta(minutes=30)).time()
            override = DoctorAvailabilityOverride(
                doctor_id=doctor.id,
                date=selected_date,
                start_time=st,
                end_time=et,
                is_available=False # Explicitly block
            )
            db.session.add(override)

        # Create ADDING overrides (is_available=True)
        for slot_str in to_add:
            st = datetime.strptime(slot_str, '%H:%M').time()
            et = (datetime.combine(datetime.today(), st) + timedelta(minutes=30)).time()
            override = DoctorAvailabilityOverride(
                doctor_id=doctor.id,
                date=selected_date,
                start_time=st,
                end_time=et,
                is_available=True # Explicitly available
            )
            db.session.add(override)
            
        db.session.commit()
        flash('Availability updated for the selected date.', 'success')
        
        if selected_date:
            return redirect(url_for('doctor.manage_slots') + f'?date={selected_date.strftime("%Y-%m-%d")}')
        return redirect(url_for('doctor.manage_slots'))

    # If a date query param exists, populate
    qdate = request.args.get('date')
    if qdate:
        try:
            selected_date = datetime.strptime(qdate, '%Y-%m-%d').date()
            form.date.data = selected_date
        except Exception:
            selected_date = None

    if selected_date is None and request.method == 'GET':
        # default to today
        selected_date = date.today()
        form.date.data = selected_date

    if selected_date:
        day_enum = get_weekday_enum_for_date(selected_date)

        # Build base weekly slots
        weekly_slots = build_slots_from_availability(doctor, day_enum)

        # Apply overrides for the date
        overrides = { (o.start_time.strftime('%H:%M')): o for o in DoctorAvailabilityOverride.query.filter_by(doctor_id=doctor.id, date=selected_date).all() }

        # Find booked appointments for that doctor on that date
        appts = Appointment.query.filter_by(doctor_id=doctor.id, date=selected_date, status=AppointmentStatus.BOOKED).all()
        booked_times = { a.time.strftime('%H:%M') for a in appts }

        # Include weekly slots and any override-only slots
        seen = set()
        for st, et, label in weekly_slots:
            seen.add(label)
            override = overrides.get(label)
            is_available = True if override is None else override.is_available
            is_booked = label in booked_times
            slots_display.append({'time': label, 'is_weekly': True, 'override': override, 'is_available': is_available, 'is_booked': is_booked})

        # Add overrides that are not part of weekly (explicitly added)
        for label, o in overrides.items():
            if label not in seen:
                is_booked = label in booked_times
                slots_display.append({'time': label, 'is_weekly': False, 'override': o, 'is_available': o.is_available, 'is_booked': is_booked})

        # Sort slots_display by time
        slots_display.sort(key=lambda x: datetime.strptime(x['time'], '%H:%M').time())

        # Pre-select form slots for currently available slots (overrides that set availability true OR weekly slots present)
        preselected = [s['time'] for s in slots_display if s['is_available']]
        form.slots.data = preselected

    return render_template('doctor/manage_slots.html', form=form, slots=slots_display, selected_date=selected_date)

@doctor_bp.route('/patient/<int:patient_id>/history')
@login_required
def patient_history(patient_id):
    if current_user.role != 'Doctor':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    patient = Patient.query.get_or_404(patient_id)
    
    appointments = Appointment.query.filter_by(
        patient_id=patient.id, 
        doctor_id=current_user.doctor_profile.id
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()

    return render_template(
        'doctor/patient_history.html', 
        patient=patient, 
        appointments=appointments
    )

@doctor_bp.route('/appointment/<int:appointment_id>/treat', methods=['GET', 'POST'])
@login_required
def treat_patient(appointment_id):
    if current_user.role != 'Doctor':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.doctor_id != current_user.doctor_profile.id:
        abort(403)

    form = TreatmentForm()
    if form.validate_on_submit():
        new_treatment = Treatment(
            appointment_id=appointment.id,
            disease=form.diagnosis.data,
            diagnosis=form.diagnosis.data,
            prescription=form.prescription.data,
            notes=form.notes.data
        )
        db.session.add(new_treatment)
        
        appointment.status = AppointmentStatus.COMPLETED
        db.session.commit()
        
        flash('Treatment has been recorded and appointment marked as completed.', 'success')
        return redirect(url_for('doctor.dashboard'))

    return render_template('doctor/treatment_form.html', form=form, appointment=appointment)

@doctor_bp.route('/appointment/<int:appointment_id>/update_status', methods=['POST'])
@login_required
def update_appointment_status(appointment_id):
    if current_user.role != 'Doctor':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.doctor_id != current_user.doctor_profile.id:
        abort(403)

    new_status = request.form.get('status')
    if new_status in [status.name for status in AppointmentStatus]:
        appointment.status = AppointmentStatus[new_status]
        db.session.commit()
        flash(f'Appointment status updated to {new_status}.', 'success')
    else:
        flash('Invalid status.', 'danger')

    return redirect(url_for('doctor.dashboard'))