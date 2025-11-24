# 🏥 Hospital Management System - V1

A web-based **Hospital Management System** built using **Flask, SQLite, HTML/CSS/Bootstrap, and Jinja2**.  
This system provides role-based access for **Admins** and **Users** to efficiently manage hospital operations like doctors, patients, appointments, and schedules.

---

## ✨ Features

### 👩‍⚕️ Admin
- Manage doctors (add, update, delete, view).
- Manage patients and their records.
- Approve or reject appointments.
- View overall hospital statistics.

### 🧑‍💻 User (Patient)
- Register and login securely.
- Search and view doctors by specialization.
- Book and manage appointments.
- View personal appointment history.

---

## 🛠️ Tech Stack
- **Backend:** Flask (Python)
- **Frontend:** HTML, CSS, Bootstrap, Jinja2 Templates
- **Database:** SQLite
- **Authentication:** Flask-Login & Werkzeug Security

---

## 📂 Project Structure
<img width="443" height="331" alt="image" src="https://github.com/user-attachments/assets/6e5bd9ee-8760-4dc9-963e-c78354de22db" />

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/<your-username>/Hospital-Management-System.git
cd Hospital-Management-System
```

### 2️⃣ Create & activate virtual environment

python -m venv venv

venv\Scripts\activate   # On Windows

source venv/bin/activate # On Mac/Linux

### 3️⃣ Install dependencies

pip install -r requirements.txt

### 4️⃣ Run the application

python app.py

### 5️⃣ Open in browser

http://127.0.0.1:5000/

---

## 🔐 Default Roles

Admin Login → Created via database seeding.

Users → Can register directly from the portal

---

## 🚀 Future Enhancements

Role for Doctors with dashboard access.

Appointment reminders via email/SMS.

Integration with external APIs for reports.

Improved UI with Vue/React frontend (next version).

---
