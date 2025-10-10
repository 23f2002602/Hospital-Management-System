from flask import Flask, render_template, redirect, url_for, flash, request, Blueprint, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from flask_login import login_required, current_user
from collections import defaultdict
from datetime import date, datetime, timedelta
from models import *
from sqlalchemy.orm import joinedload
from sqlalchemy import func, case
from forms import DoctorSetupForm, AppointmentForm
from wtforms import StringField, DateField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
