from routes.routes import *

admin_bp = Blueprint('admin', __name__)

# Admin Dashboard

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    today = date.today()
    todays_appointments = Appointment.query.filter(Appointment.date == today)
    future_appointments = Appointment.query.filter(Appointment.date > today).order_by(Appointment.date).all()

    return render_template(
        'admin/dashboard.html',
        todays_appointments = todays_appointments,
        future_appointments =future_appointments
    )

###  APPOINTMENT MANAGEMENT ###

@admin_bp.route('/appointments')
@login_required
def view_appt():
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    all_appointments = Appointment.query.options(
        joinedload(Appointment.patient).joinedload(Patient.user),
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.treatment)
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()

    return render_template('admin/appts.html', appointments=all_appointments)

@admin_bp.route('/appointment/delete/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    appt = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appt)
    db.session.commit()
    flash('Appointment deleted successfully', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/appointment/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def edit_appt(appointment_id):
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    appt = Appointment.query.get_or_404(appointment_id)
    form = AppointmentForm(obj=appt)

    # Populate doctor choices immediately (Required for validation)
    all_doctors = Doctor.query.join(User).all()
    form.doctor_id.choices = [
        (d.id, f"Dr. {d.user.name} ({d.specialization})") for d in all_doctors
    ]

    # Handle Time Choices for Validation
    # Determine which doctor and date to use (Form data takes precedence on POST)
    target_doctor_id = appt.doctor_id
    target_date = appt.date

    if request.method == 'POST':
        try:
            target_doctor_id = int(request.form.get('doctor_id', appt.doctor_id))
            date_str = request.form.get('date')
            if date_str:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Fetch available slots for the target doctor/date
    available_slots = []
    if target_doctor_id and target_date:
        day_enum = DayOfWeek[target_date.strftime('%A').upper()]
        slots = DoctorAvailability.query.filter_by(
            doctor_id=target_doctor_id, 
            day=day_enum
        ).order_by(DoctorAvailability.start_time).all()
        available_slots = [(s.start_time.strftime('%H:%M'), s.start_time.strftime('%H:%M')) for s in slots]

    form.time.choices = available_slots

    # Ensure the current appointment time is in choices so validation doesn't fail on existing data
    current_time_str = appt.time.strftime('%H:%M')
    if (current_time_str, current_time_str) not in form.time.choices:
        form.time.choices.append((current_time_str, current_time_str))
        form.time.choices.sort()

    if form.validate_on_submit():
        try:
            appt.doctor_id = form.doctor_id.data
            appt.date = form.date.data
            appt.time = datetime.strptime(form.time.data, '%H:%M').time()
            appt.problem = form.problem.data

            db.session.commit()
            flash('Appointment updated successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while updating: {e}", "danger")

    if request.method == 'GET':
        form.doctor_id.data = appt.doctor_id
        form.date.data = appt.date
        form.time.data = appt.time.strftime('%H:%M')
        form.problem.data = appt.problem

    return render_template('admin/doctor_setup.html', form=form, edit_mode=True, appointment=appt, entity='appointment')

### DOCTOR MANAGEMENT ###

@admin_bp.route('/doctors')
@login_required
def view_doctors():
    # Restrict access to admin only
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    doctors_with_stats = db.session.query(
        Doctor,
        func.count(case((Appointment.status == AppointmentStatus.COMPLETED, Appointment.id))).label('completed_count'),
        func.count(case((Appointment.status == AppointmentStatus.BOOKED, Appointment.id))).label('pending_count'),
        func.count(case((Appointment.date == date.today(), Appointment.id))).label('today_count')
    ).outerjoin(Appointment).group_by(Doctor.id).all()

        # Append data as a dict
    doctor_data = [{
        'id': doc.id,
        'name': doc.user.name if doc.user else 'N/A',
        'specialization': doc.specialization,
        'today_count': today_count,
        'completed_count': completed_count,
        'pending_count': pending_count
    } for doc, completed_count, pending_count, today_count in doctors_with_stats]

    return render_template(
        'admin/doctors.html',
        doctors=doctor_data
    )

@admin_bp.route('/doctor/<int:doctor_id>')
@login_required
def view_doctor_detail(doctor_id):
    if not current_user.role == 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    doctor = Doctor.query.get_or_404(doctor_id)
    availability_schedule = defaultdict(list)

    slots = DoctorAvailability.query.filter_by(doctor_id=doctor.id).order_by(
        DoctorAvailability.day, 
        DoctorAvailability.start_time
    ).all()
    for slot in slots:
        time_format = f"{slot.start_time.strftime('%H:%M')}"
        availability_schedule[slot.day.value].append(time_format)
    
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()

    today = date.today()
    today_count = sum(1 for appt in appointments if appt.date == today)
    completed_count = sum(1 for appt in appointments if appt.status == AppointmentStatus.COMPLETED)
    pending_count = sum(1 for appt in appointments if appt.status == AppointmentStatus.BOOKED)

    return render_template(
        'admin/doctor_detail.html',
        doctor=doctor,
        availability_schedule=availability_schedule, 
        appointments=appointments,
        today_count=today_count,
        completed_count=completed_count,
        pending_count=pending_count
    )

@admin_bp.route('/doctor/edit/<int:doctor_id>', methods = ["GET", "POST"])
@login_required
def edit_doctor(doctor_id):
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))

    doctor = Doctor.query.get_or_404(doctor_id)
    form = DoctorSetupForm(obj = doctor)

    if request.method == 'GET':
        existing_slots = DoctorAvailability.query.filter_by(doctor_id=doctor.id).all()
        if existing_slots:
            days_set = {slot.day.name for slot in existing_slots}
            slots_set = {slot.start_time.strftime('%H:%M') for slot in existing_slots}

            form.available_days.data = list(days_set)
            form.available_slots.data = list(slots_set)
    if form.validate_on_submit():
        try:
            doctor.specialization = form.specialization.data
            DoctorAvailability.query.filter_by(doctor_id=doctor.id).delete()
            selected_days = form.available_days.data
            selected_slots = form.available_slots.data

            for day_str in selected_days:
                day_enum = DayOfWeek[day_str.upper()]
                for slot_str in selected_slots:
                    start_time = datetime.strptime(slot_str, '%H:%M').time()
                    end_time_dt = datetime.combine(datetime.today(), start_time) + timedelta(minutes=30)
                    end_time = end_time_dt.time()

                    new_slot = DoctorAvailability(
                        doctor_id=doctor.id,
                        day=day_enum,
                        start_time=start_time,
                        end_time=end_time
                    )
                    db.session.add(new_slot)
            db.session.commit()

            flash(f'Doctor {doctor.user.name}\'s profile has been updated successfully!', 'success')
            return redirect(url_for('admin.view_doctor_detail', doctor_id=doctor.id))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while updating: {e}", "danger")

    return render_template('admin/doctor_setup.html', form=form, edit_mode=True, doctor=doctor, entity='doctor')


@admin_bp.route('/doctor/delete/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def delete_doctor(doctor_id):
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    doctor = Doctor.query.get_or_404(doctor_id)
    user = User.query.get(doctor.user_id)

    db.session.delete(doctor)
    if user and user.role == 'Doctor':
        db.session.delete(user)
    
    db.session.commit()

    flash('Doctor and associated data deleted successfully', 'success')
    return redirect(url_for('admin.view_doctors'))


### PATIENT MANAGEMENT ###


@admin_bp.route('/patients')
@login_required
def view_patients():
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    from models import Patient
    patients = Patient.query.all()
    patients_data = []

    for p in patients:
        today = date.today()
        age = today.year - p.dob.year - ((today.month, today.day) < (p.dob.month, p.dob.day))
  
        latest_appt = None
        if p.appointments:
            latest_appt = max(p.appointments, key = lambda appt:(appt.date, appt.time))

        patients_data.append({
            'id': p.id,
            'name': p.user.name,
            'dob': p.dob,
            'age': age,
            'phone_number': p.phone_number,
            'latest_appointment': latest_appt,
            'total_appointments': len(p.appointments)
        })
    return render_template('admin/patients.html', patients=patients_data)


@admin_bp.route('/patient/<int:patient_id>')
@login_required
def view_patient_detail(patient_id):
    if current_user.role != "Admin" :
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    from models import Patient, Appointment
    patient = Patient.query.get_or_404(patient_id)
    appointments_list = Appointment.query.filter_by(patient_id=patient.id).all()

    return render_template('admin/view_patient.html',appointment=appointments_list, patient=patient)


@admin_bp.route('/patient/delete/<int:patient_id>', methods = ["GET", "POST"])
@login_required
def delete_patient(patient_id):
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    patient = Patient.query.get_or_404(patient_id)
    user = User.query.get(patient.user_id)

    # Delete associated appointments and treatments
    for appt in patient.appointments:
        if appt.treatment:
            db.session.delete(appt.treatment)
        db.session.delete(appt)
    
    db.session.delete(patient)
    if user:
        db.session.delete(user)
    
    db.session.commit()
    flash('Patient and associated data deleted successfully', 'success')
    return redirect(url_for('admin.view_patients'))

@admin_bp.route('/patient/edit/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    patient = Patient.query.get_or_404(patient_id)
    user = User.query.get_or_404(patient.user_id)

    from forms import PatientSetupForm
    form = PatientSetupForm(obj=patient)

    if form.validate_on_submit():
        try:
            user.name = form.name.data
            patient.dob = form.dob.data
            patient.phone_number = form.phone_number.data

            db.session.commit()
            flash('Patient details updated successfully', 'success')
            return redirect(url_for('admin.view_patients', patient_id=patient.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while updating: {e}", "danger")
    
    if request.method == 'GET':
        form.name.data = user.name
        form.phone_number.data = patient.phone_number
        form.dob.data = patient.dob

    return render_template('admin/doctor_setup.html', form=form, patient=patient, edit_mode =True, entity = 'patient')