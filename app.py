from flask import Flask
from config import Config
from database import db
from routes.admin import admin_bp
from routes.patients import patient_bp
from routes.doctor import doctor_bp
from models import User
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login' # redirects to login page if not logged in

    # Register Blueprints
    app.register_blueprint(admin_bp, url_prefix = '/admin')
    app.register_blueprint(doctor_bp, url_prefix = '/doctor')
    app.register_blueprint(patient_bp, url_prefix = '/patient')


    with app.app_context():
        db.create_all()
        #Create admin user if it doesn't exist
        # app.py (fix admin creation)
        if not User.query.filter_by(role='Admin').first():
            hashed_password = generate_password_hash('admin_password')
            admin = User(
                username='admin',
                name='Administrator',
                email='admin123@gmail.com',
                password= hashed_password,
                role='Admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user added successfully.")
    
    return app





