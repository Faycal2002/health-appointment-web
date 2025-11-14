from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# setting up the flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smarthealth.db'  # database setup
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)  # database link



class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100))  # path for image file in static
    description = db.Column(db.String(300))  # small text about doctor

    # link to appointments (so admin can see which patients booked)
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)


# appointment table (patients fill this in form)
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    ethnicity = db.Column(db.String(50), nullable=False)
    symptoms = db.Column(db.String(300), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))  # link to doctor table

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/doctor_login")
def doctor_login():
    # no password for now just direct route to admin
    return redirect(url_for("admin"))

@app.route("/admin")
def admin():
    doctors = Doctor.query.all()  
    appointments = Appointment.query.all()  
    return render_template("admin.html", doctors=doctors, appointments=appointments)


@app.route("/search")
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

# this is the booking route (for patient)
@app.route("/book/<int:doctor_id>", methods=["GET", "POST"])
def book_appointment(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    message = None  # error message if missing
    success = None  # message if done

    if request.method == "POST":
        # getting data from form
        name = request.form.get("name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        ethnicity = request.form.get("ethnicity")
        symptoms = request.form.get("symptoms")
        date = request.form.get("date")

        # check if fields are empty
        if not name or not age or not gender or not ethnicity or not symptoms or not date:
            message = "Please fill in all fields properly."
        else:
            # create new appointment record
            new_appt = Appointment(
                patient_name=name,
                age=age,
                gender=gender,
                ethnicity=ethnicity,
                symptoms=symptoms,
                date=date,
                doctor_id=doctor.id
            )
            db.session.add(new_appt)
            db.session.commit()
            # redirect to confirmation page after successful booking
            return redirect(url_for("appointment_confirmed", doctor_id=doctor.id))

    # if GET, show booking form
    return render_template("book_appointment.html", doctor=doctor, message=message, success=success)


# confirmation page route
@app.route("/appointment_confirmed/<int:doctor_id>")
def appointment_confirmed(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    # this just shows a page saying booked successfully
    return render_template("appointment_confirmed.html", doctor=doctor)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # makes db if not exists

        # only adds demo data once (so it doesn't repeat)
        if not Doctor.query.first():
            doctors = [
                Doctor(name="Dr. John Smith", specialty="Cardiology", location="Sheffield",
                       image="img/doctor1.jpg", description="Expert in cardiovascular health and patient care."),
                Doctor(name="Dr. Emma Lee", specialty="Dermatology", location="Leeds",
                       image="img/doctor2.jpg", description="Specialist in skincare, acne treatment, and laser therapy."),
                Doctor(name="Dr. James Patel", specialty="Orthopedic Surgery", location="Birmingham",
                       image="img/doctor3.jpg", description="Experienced orthopedic surgeon focusing on joint and spine health."),
                Doctor(name="Dr. Olivia Wright", specialty="Neurology", location="Nottingham",
                       image="img/doctor4.jpg", description="Neurology expert specializing in migraines and cognitive disorders."),
                Doctor(name="Dr. Noah Khan", specialty="Pediatrics", location="Manchester",
                       image="img/doctor5.jpg", description="Pediatrician dedicated to child development and family care."),
                Doctor(name="Dr. Sarah Benali", specialty="Psychiatry", location="London",
                       image="img/doctor6.jpg", description="Compassionate psychiatrist supporting mental wellness.")
            ]
            db.session.add_all(doctors)
            db.session.commit()  # save demo doctors
            # just to make sure there’s data for the search page

    # running on debug so can see errors
    app.run(debug=True)
