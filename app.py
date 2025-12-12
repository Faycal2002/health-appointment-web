from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import os
from werkzeug.utils import secure_filename
from functools import wraps

# -------------------------
# FLASK APP CONFIG
# -------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smarthealth.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'faycel_habchi123456789'

# dossier pour les images uploadées
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)


# -------------------------
# DATABASE MODELS
# -------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # "admin" ou "patient"


class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100))   # ex : "uploads/monimage.jpg"
    description = db.Column(db.String(300))
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    symptoms = db.Column(db.String(300), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    hour = db.Column(db.String(5), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


# -------------------------
# CONTEXT PROCESSORS (NAVBAR)
# -------------------------
@app.context_processor
def inject_specialties():
    specialties = db.session.query(Doctor.specialty).distinct().all()
    specialties = [s[0] for s in specialties]
    return {"nav_specialties": specialties}


@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    role = session.get("user_role")

    user = None
    if user_id:
        user = User.query.get(user_id)

    return dict(current_user=user, current_role=role)


# -------------------------
# DECORATEUR login_required
# -------------------------
def login_required(role=None):
    """
    Si role=None  -> juste connecté
    Si role='admin' -> connecté ET admin uniquement
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            user_id = session.get("user_id")
            user_role = (session.get("user_role") or "").strip().lower()

            if not user_id:
                return redirect(url_for("login", next=request.path))

            if role is not None and user_role != role.strip().lower():
                return redirect(url_for("home"))

            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator


# -------------------------
# ROUTES PUBLIQUES
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        error = None

        # ----- LOGIN -----
        if "login_email" in request.form:
            email = (request.form.get("login_email") or "").strip()
            password = request.form.get("login_password") or ""

            if not email or not password:
                error = "Please enter both email and password."
                flash(error, "danger")
                return render_template("login.html")

            user = User.query.filter_by(email=email).first()

            if not user:
                error = "No account found with this email."
            elif not check_password_hash(user.password, password):
                error = "Incorrect password."

            if error:
                flash(error, "danger")
            else:
                role = (user.role or "patient").strip().lower()
                user.role = role  # normalise dans la DB aussi
                db.session.commit()

                session["user_id"] = user.id
                session["user_role"] = role

                flash("Login successful!", "success")

                if role == "admin":
                    return redirect(url_for("admin"))
                else:
                    next_page = request.args.get("next")
                    return redirect(next_page or url_for("search"))

        # ----- REGISTER -----
        elif "firstname" in request.form:
            firstname = request.form.get("firstname")
            lastname = request.form.get("lastname")
            email = request.form.get("email")
            password = request.form.get("password")
            address = request.form.get("address")
            number = request.form.get("number")

            if User.query.filter_by(email=email).first():
                flash("Email already exists.", "danger")
                return render_template("login.html")

            hashed_pw = generate_password_hash(password)
            new_user = User(
                firstname=firstname,
                lastname=lastname,
                email=email,
                password=hashed_pw,
                address=address,
                number=int(number),
                role="patient"
            )
            db.session.add(new_user)
            db.session.commit()

            session["user_id"] = new_user.id
            session["user_role"] = "patient"

            flash("Registration successful!", "success")
            return redirect(url_for("search"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# -------------------------
# ADMIN DASHBOARD
# -------------------------
@app.route("/admin")
@login_required(role="admin")
def admin():
    doctors = Doctor.query.all()
    users = User.query.all()
    appointments = Appointment.query.all()
    return render_template("admin.html", doctors=doctors, users=users, appointments=appointments)


# ---------- DOCTORS ----------
@app.route("/admin/add_doctor", methods=["POST"])
@login_required(role="admin")
def add_doctor():
    name = request.form.get("name")
    specialty = request.form.get("specialty")
    location = request.form.get("location")
    description = request.form.get("description")

    image_file = request.files.get("image")
    if image_file and image_file.filename != "":
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image_file.save(image_path)
        image_field = f"uploads/{filename}"
    else:
        image_field = "img/doctor1.jpg"

    new_doctor = Doctor(
        name=name,
        specialty=specialty,
        location=location,
        description=description,
        image=image_field
    )

    db.session.add(new_doctor)
    db.session.commit()
    flash("Doctor added successfully.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/delete_doctor/<int:doctor_id>", methods=["POST"])
@login_required(role="admin")
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    flash("Doctor deleted.", "info")
    return redirect(url_for("admin"))


@app.route("/admin/update_doctor/<int:doctor_id>", methods=["POST"])
@login_required(role="admin")
def update_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    doctor.name = request.form.get("name")
    doctor.specialty = request.form.get("specialty")
    doctor.location = request.form.get("location")
    doctor.description = request.form.get("description")

    image_file = request.files.get("image")
    if image_file and image_file.filename != "":
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image_file.save(image_path)
        doctor.image = f"uploads/{filename}"

    db.session.commit()
    flash("Doctor updated successfully!", "success")
    return redirect(url_for("admin"))


# ---------- USERS ----------
@app.route("/admin/add_user", methods=["POST"])
@login_required(role="admin")
def add_user():
    firstname = request.form.get("firstname")
    lastname = request.form.get("lastname")
    address = request.form.get("address")
    number = request.form.get("number")
    email = request.form.get("email")
    password = request.form.get("password")
    role_raw = request.form.get("role", "patient")

    role = (role_raw or "patient").strip().lower()

    if not all([firstname, lastname, address, number, email, password]):
        flash("Please fill all user fields.", "danger")
        return redirect(url_for("admin"))

    if User.query.filter_by(email=email).first():
        flash("Email already exists.", "danger")
        return redirect(url_for("admin"))

    hashed_pw = generate_password_hash(password)

    new_user = User(
        firstname=firstname,
        lastname=lastname,
        address=address,
        number=int(number),
        email=email,
        password=hashed_pw,
        role=role
    )
    db.session.add(new_user)
    db.session.commit()
    flash("User added successfully.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required(role="admin")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "info")
    return redirect(url_for("admin"))


@app.route("/admin/update_user/<int:user_id>", methods=["POST"])
@login_required(role="admin")
def update_user(user_id):
    user = User.query.get_or_404(user_id)

    user.firstname = request.form.get("firstname")
    user.lastname = request.form.get("lastname")
    user.address = request.form.get("address")
    user.number = request.form.get("number")
    user.email = request.form.get("email")

    role_raw = request.form.get("role")
    user.role = (role_raw or user.role).strip().lower()

    db.session.commit()
    flash("User updated successfully!", "success")
    return redirect(url_for("admin"))


# ---------- APPOINTMENTS (ADMIN) ----------
@app.route("/admin/add_appointment", methods=["POST"])
@login_required(role="admin")
def add_appointment():
    patient_name = request.form.get("patient_name")
    doctor_id = request.form.get("doctor_id")
    date_str = request.form.get("date")
    hour = request.form.get("hour")
    symptoms = request.form.get("symptoms")

    if not all([patient_name, doctor_id, date_str, hour, symptoms]):
        flash("Please fill all appointment fields.", "danger")
        return redirect(url_for("admin"))

    new_appt = Appointment(
        patient_name=patient_name,
        age=0,
        gender="N/A",
        symptoms=symptoms,
        date=date_str,
        hour=hour,
        doctor_id=int(doctor_id),
        user_id=None
    )
    db.session.add(new_appt)
    db.session.commit()
    flash("Appointment added successfully.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/delete_appointment/<int:appt_id>", methods=["POST"])
@login_required(role="admin")
def delete_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    db.session.delete(appt)
    db.session.commit()
    flash("Appointment deleted.", "info")
    return redirect(url_for("admin"))


@app.route("/admin/update_appointment/<int:appt_id>", methods=["POST"])
@login_required(role="admin")
def update_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)

    appt.patient_name = request.form.get("patient_name")
    appt.date = request.form.get("date")
    appt.hour = request.form.get("hour")
    appt.symptoms = request.form.get("symptoms")
    appt.doctor_id = request.form.get("doctor_id")

    db.session.commit()
    flash("Appointment updated successfully!", "success")
    return redirect(url_for("admin"))


# -------------------------
# ROUTES PATIENT (protégées)
# -------------------------
@app.route("/search")
@login_required()
def search():
    query = request.args.get("query", "")

    if query:
        doctors = Doctor.query.filter(
            (Doctor.name.like(f"%{query}%")) |
            (Doctor.specialty.like(f"%{query}%")) |
            (Doctor.location.like(f"%{query}%"))
        ).all()
    else:
        doctors = Doctor.query.all()

    return render_template("search.html", doctors=doctors, query=query)


@app.route("/book/<int:doctor_id>", methods=["GET", "POST"])
@login_required()
def book_appointment(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    message = None

    if request.method == "POST":
        name = request.form.get("name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        symptoms = request.form.get("symptoms")
        appointment_date = request.form.get("date")
        time_str = request.form.get("time")

        if not all([name, age, gender, symptoms, appointment_date, time_str]):
            message = "Please fill in all fields."
        else:
            new_appt = Appointment(
                patient_name=name,
                age=int(age),
                gender=gender,
                symptoms=symptoms,
                date=appointment_date,
                hour=time_str,
                doctor_id=doctor.id,
                user_id=session.get("user_id")
            )
            db.session.add(new_appt)
            db.session.commit()
            return redirect(url_for("appointment_confirmed", doctor_id=doctor.id))

    today = date.today().isoformat()
    return render_template("book_appointment.html", doctor=doctor, today=today, message=message)


@app.route("/appointment_confirmed/<int:doctor_id>")
@login_required()
def appointment_confirmed(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    return render_template("appointment_confirmed.html", doctor=doctor)

@app.route("/appointments")
@login_required()
def appointments():
    user_id = session.get("user_id")

    my_appointments = (
        Appointment.query
        .filter_by(user_id=user_id)
        .order_by(Appointment.date.desc(), Appointment.hour.desc())
        .all()
    )

    return render_template("appointments.html", appointments=my_appointments)


# -------------------------
# CREATE DB + ADMIN PAR DÉFAUT
# -------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
