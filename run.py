from flask_login import login_user, login_required, current_user, logout_user
from app import create_app
from flask import render_template, request, redirect, url_for, flash
from forms import LoginForm, RegisterForm, DoctorSetupForm
from models import User, db, Doctor
from werkzeug.security import generate_password_hash, check_password_hash

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
                    return redirect(url_for('doctor_setup'))
                flash('Login Successful !', "success")
                return redirect(url_for('admin.dashboard'))
            
            else:
                flash('Login Successful !', "success")
                return redirect (url_for('patient_dashboard'))
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
            registerform.username.errors.append("This username is already taken. Choose a different one.")
        
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

@app.route('/doctor/setup', methods = ['GET', 'POST'])
@login_required
def doctor_setup():
    form = DoctorSetupForm()
    
    if form.validate_on_submit():
        # Suppose form.available_slots.data = ['09:00', '10:00', '11:00']
        available_slots = ",".join(form.available_slots.data)  # '09:00,10:00,11:00'

        doctor = Doctor(
            user_id=current_user.id,
            specialization=form.specialization.data,
            available_days=",".join(form.available_days.data),  # same for days
            available_slots=available_slots
        )
        db.session.add(doctor)
        db.session.commit()


        flash("Doctor profile created successfully!", "success")
        return redirect(url_for("admin.dashboard"))  # use correct endpoint

    return render_template("doctor_setup.html", form=form, edit_mode=False)


@app.route('/logout')
@login_required
def logout():
    logout_user()  # Logs out the current user
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('login'))  # Redirect to your login page

if __name__ == "__main__":
    app.run(debug=True)