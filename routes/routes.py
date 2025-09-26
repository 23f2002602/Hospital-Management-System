from flask import Flask, render_template, redirect, url_for, flash, request, Blueprint
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from flask_login import login_required, current_user

