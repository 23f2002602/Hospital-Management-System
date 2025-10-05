from flask_login import login_user, login_required, current_user, logout_user
from app import create_app
from flask import render_template, request, redirect, url_for, flash
from forms import LoginForm, RegisterForm, DoctorSetupForm, PatientSetupForm
from models import User, db, Doctor, DoctorAvailability, DayOfWeek, Patient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = create_app()

@app.route('/', methods=["GET", "POST"])
def login() :
    loginform = LoginForm()
    if loginform.validate_on_submit():
        user = User.query.filter_by(email = loginform.email.data).first()

        if user and check_password_hash(user.password, loginform.password.data):
            login_user(user)
            if user.role == 'Admin':
                flash('Login Successful !', "success")
                return redirect(url_for('admin.dashboard'))
            
            elif user.role == 'Doctor':
                if not user.doctor_profile:
                    flash('Please complete your profile before proceeding.', 'info')
                    return redirect(url_for('doctor_setup'))
                flash('Login Successful !', "success")
                return redirect(url_for('doctor.dashboard'))
            
            elif user.role == 'Patient': # PATIENT
                if not user.patient_profile:
                    flash('Please complete your profile before proceeding.', 'info')
                    return redirect(url_for('patient_setup'))
                flash('Login Successful !', "success")
                return redirect (url_for('patient.dashboard'))
        else:
            flash('Login Failed. Check email and password', 'danger')
    
    return render_template('index.html', form=loginform)


@app.route('/register', methods=["GET", "POST"])
def register():
    registerform = RegisterForm()
    if registerform.validate_on_submit():
        user_by_username = User.query.filter_by(username = registerform.username.data).first()
        user_by_email = User.query.filter_by(email = registerform.email.data).first()

        if user_by_username and user_by_email :
            flash("User with this username and email already exists. Please login.", "info")
            return redirect(url_for("login"))
        
        elif user_by_username:
            registerform.username.errors.append("This username is already taken. Choose a different one.")
        
        elif user_by_email:
            registerform.email.errors.append("This email is already taken. Choose a different one.")
        
        else:
            hashed_password = generate_password_hash(registerform.password.data)
            
            new_user = User(username = registerform.username.data, 
                            name = registerform.name.data,
                            email = registerform.email.data,
                            password = hashed_password,
                            role = registerform.role.data)
            
            db.session.add(new_user)
            db.session.commit()

            flash('Account created successfully! Please login.', 'success')
            
            return redirect(url_for('login'))

    return render_template('register.html', form = registerform)

# In run.py

# Make sure all necessary models and forms are imported at the top
from forms import DoctorSetupForm
from models import db, Doctor, DoctorAvailability, DayOfWeek
from datetime import datetime, timedelta

@app.route('/doctor/setup', methods=['GET', 'POST'])
@login_required
def doctor_setup():
    # Authorization checks
    if current_user.role != 'Doctor':
        flash("This page is only for doctors.", "warning")
        return redirect(url_for('login'))
    if current_user.doctor_profile:
        flash("You have already completed your profile setup.", "info")
        return redirect(url_for('admin.dashboard')) 

    form = DoctorSetupForm()
    
    if form.validate_on_submit():
        try:
            new_doctor = Doctor(
                user_id=current_user.id,
                specialization=form.specialization.data
            )
            db.session.add(new_doctor)
            db.session.commit()

            selected_days = form.available_days.data
            selected_slots = form.available_slots.data

            for day_str in selected_days:
                day_enum = DayOfWeek[day_str.upper()] 
                
                for slot_str in selected_slots:
                    start_time = datetime.strptime(slot_str, '%H:%M').time()
                    end_time_dt = datetime.combine(datetime.today(), start_time) + timedelta(minutes=30)
                    end_time = end_time_dt.time()

                    availability_slot = DoctorAvailability(
                        doctor_id=new_doctor.id,
                        day=day_enum,
                        start_time=start_time,
                        end_time=end_time
                    )
                    db.session.add(availability_slot)
            
            db.session.commit()

            flash("Doctor profile created successfully!", "success")
            return redirect(url_for("admin.dashboard"))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", "danger")

    return render_template("doctor_setup.html", form=form, entity='doctor', edit_mode=False)

@app.route('/patient/setup', methods=['GET', 'POST'])
@login_required
def patient_setup():
    if current_user.role != 'Patient':
        flash('This page is only for patients', 'warning')
        return redirect(url_for('login'))
    if current_user.patient_profile:
        flash('You have already complted your profile setup.', 'info')
        return redirect(url_for('patient.dashaboard'))
    
    form = PatientSetupForm()

    if form.validate_on_submit():
        try:
            new_patient = Patient(
                user_id = current_user.id,
                dob = form.dob.data,
                phone_number = form.phone_number.data
            )

            current_user.name = form.name.data

            db.session.add(new_patient)
            db.session.commit()

            flash("Your profile has been completed successfully!", "success")
            return redirect(url_for('patient.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occured : {e}", "danger")
    
    elif request.method == 'GET':
        form.name.data = current_user.name

    return render_template(
        "doctor_setup.html", form=form, entity='patient', edit_mode=False)

@app.route('/logout')
@login_required
def logout():
    logout_user()  # Logs out the current user
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('login'))  # Redirect to your login page

if __name__ == "__main__":
    app.run(debug=True)