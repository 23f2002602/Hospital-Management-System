from routes.routes import *
from models import *
from forms import TreatmentForm
from datetime import date

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'Doctor':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    doctor = current_user.doctor_profile
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

    return render_template(
        'doctor/dashboard.html', 
        doctor=doctor, 
        upcoming_appointments=upcoming_appointments,
        completed_appointments=completed_appointments
    )

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