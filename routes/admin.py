from routes.routes import *
from datetime import date
from models import Appointment
admin_bp = Blueprint('admin', __name__)

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
        'admin_dashboard.html',
        todays_appointments = todays_appointments,
        future_appointments =future_appointments
    )

@admin_bp.route('/appointment/delete/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    appt = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appt)
    db.session.commit()
    flash('Appointment deleted scuccessfully', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/doctors')
@login_required
def view_doctors():
    # Restrict access to admin only
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    # Get all doctors
    from models import Doctor
    doctors = Doctor.query.all()
    doctor_data = []

    for doc in doctors:
        # Count appointments for today
        today_count = Appointment.query.filter_by(doctor_id=doc.id, date=date.today()).count()
        # Count completed appointments
        completed_count = Appointment.query.filter_by(doctor_id=doc.id, status='Completed').count()
        # Count pending appointments
        pending_count = Appointment.query.filter_by(doctor_id=doc.id, status='Pending').count()

        # Append data as a dict
        doctor_data.append({
            'id': doc.id,
            'name': doc.user.name if doc.user else 'N/A',
            'specialization': doc.specialization,
            'today_count': today_count,
            'completed_count': completed_count,
            'pending_count': pending_count
        })

    return render_template(
        'admin_doctors.html',  # make sure template is in templates/ folder
        doctors=doctor_data
    )

@admin_bp.route('/doctor/<int:doctor_id>')
@login_required
def view_doctor_detail(doctor_id):
    # Only Admin can access
    if not current_user.role == 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))

    # Get doctor
    from models import Doctor
    doctor = Doctor.query.get_or_404(doctor_id)

    # Convert available_days and available_slots from string to list if needed
    available_days = doctor.available_days
    if isinstance(available_days, str):
        available_days = available_days.split(',') if doctor.available_days else []

    available_slots = doctor.available_slots
    if isinstance(available_slots, str):
        available_slots = available_slots.split(',') if doctor.available_slots else []

    # Appointments
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()

    # Count appointments
    today = date.today()
    today_count = sum(1 for appt in appointments if appt.date == today)
    completed_count = sum(1 for appt in appointments if appt.status == 'Completed')
    pending_count = sum(1 for appt in appointments if appt.status != 'Completed')

    return render_template(
        'admin_doctor_detail.html',
        doctor=doctor,
        available_days=available_days,
        available_slots=available_slots,
        appointments=appointments,
        today_count=today_count,
        completed_count=completed_count,
        pending_count=pending_count
    )

@admin_bp.route('/doctor/<int:doctor_id>', methods = ["GET", "POST"])
@login_required
def edit_doctor(doctor_id):
    if current_user.role != 'Admin':
        flash('Access Denied', 'danger')
        return redirect(url_for('login'))
    
    from models import Doctor
    from forms import DoctorSetupForm

    doctor = Doctor.query.get_or_404(doctor_id)
    form = DoctorSetupForm(obj = doctor)

    if request.method == 'GET':
        if doctor.available_days :
            form.available_days.data = doctor.available_days.split(',')
        form.available_slots.data = doctor.available_slots

    if form.validate_on_submit:
        doctor.specialization = form.specialization.data
        doctor.available_days = ','.join(form.available_days.data)
        doctor.available_slots = form.available_slots.data

        db.session.commit()
        flash(f'Doctor {doctor.user.name} updated successfully!', 'success')
        return redirect(url_for('admin.view_doctor_detail', doctor_id=doctor.id))
    
    return render_template('doctor_setup.html', form=form, edit_mode=True)

