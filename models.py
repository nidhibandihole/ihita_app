from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()  # Single instance

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    apartment_number = db.Column(db.String(10), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

# Announcement model for moving details
class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    apartment_number = db.Column(db.String(50), nullable=False)
    move_type = db.Column(db.String(10), nullable=False)  # "Moving In" or "Moving Out"
    moving_date = db.Column(db.Date, nullable=False)
    dues_clear = db.Column(db.String(20), nullable=False)  # "Cleared" or "Pending"
    comments = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# PartyHallBooking model
class PartyHallBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    apartment_number = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    slot = db.Column(db.String(20), nullable=False)  # 'Half Day' or 'Full Day'
    payment = db.Column(db.String(10), nullable=False)
    comments = db.Column(db.Text, nullable=True)

    # AdminAnnouncement model
class AdminAnnouncement(db.Model):
    __tablename__ = 'admin_announcement'

    id = db.Column(db.Integer, primary_key=True)
    apartment_number = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(255))

# Suggestion model
class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    apartment_number = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(255))  # Optional image path

    # Staff Contact Details model
class StaffContact(db.Model):
    __tablename__ = 'staff_contact'  # <-- Add this line

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(100), nullable=False) 
    phone = db.Column(db.String(100), nullable=False)


def insert_staff_contact(name, role, phone):
    contact = StaffContact(name=name, role=role, phone=phone)
    db.session.add(contact)
    db.session.commit()

def get_all_staff_contacts():
    return StaffContact.query.all()



def insert_user(username, password, apartment_number):
    # Check if username or apartment number is already taken
    if User.query.filter_by(username=username).first() or User.query.filter_by(apartment_number=apartment_number).first():
        raise ValueError("Username or apartment number already taken.")
    # Set is_admin based on credentials
    is_admin = username == "admin" and apartment_number == "000"
    user = User(
        username=username,
        password=password,
        apartment_number=apartment_number,
        is_admin=is_admin
    )
    db.session.add(user)
    db.session.commit()

# Get User by username
def get_user_by_username(username):
    return User.query.filter_by(username=username).first()

# Insert Suggestion
def insert_suggestion(apartment_number, content, image_path=None):
    suggestion = Suggestion(apartment_number=apartment_number, content=content, image_path=image_path)
    db.session.add(suggestion)
    db.session.commit()

# Get all suggestions
def get_all_suggestions():
    return Suggestion.query.order_by(Suggestion.timestamp.desc()).all()


# Insert Party Hall Booking
def insert_booking(apartment_number, date, slot, payment, comments):
    booking = PartyHallBooking(
        apartment_number=apartment_number,
        date=date,
        slot=slot,
        payment=payment,
        comments=comments
    )
    db.session.add(booking)
    db.session.commit()

# Get all bookings
def get_all_bookings():
    return PartyHallBooking.query.order_by(PartyHallBooking.date).all()

# Get bookings by date
def get_bookings_by_date(date):
    return db.session.query(PartyHallBooking).filter(PartyHallBooking.date == date).all()

# Check if date is booked
def is_date_booked(date):
    return PartyHallBooking.query.filter_by(date=date).first() is not None

# Get moving details by apartment
def get_moving_details_by_apartment(apartment_number):
    return Announcement.query.filter_by(apartment_number=apartment_number).order_by(Announcement.timestamp.desc()).all()

# Get moving details by move type
def get_moving_details_by_move_type(move_type):
    return Announcement.query.filter_by(move_type=move_type).order_by(Announcement.timestamp.desc()).all()

# Get moving details by date
def get_moving_details_by_date(moving_date):
    return Announcement.query.filter_by(moving_date=moving_date).order_by(Announcement.timestamp.desc()).all()

def get_user_by_apartment_number(apartment_number):
    return db.session.query(User).filter_by(apartment_number=apartment_number).first()

# Get latest moving details by apartment
def get_latest_moving_details_by_apartment(apartment_number):
    return Announcement.query.filter_by(apartment_number=apartment_number).order_by(Announcement.timestamp.desc()).first()

# Get all moving details
def get_all_moving_details():
    return Announcement.query.order_by(Announcement.moving_date.desc()).all()

# Insert moving details
def insert_moving_details(apartment_number, move_type, moving_date_obj, dues_clear, comments=None):
    announcement = Announcement(
        apartment_number=apartment_number,
        move_type=move_type,
        moving_date=moving_date_obj,
        dues_clear=dues_clear,
        comments=comments
    )
    db.session.add(announcement)
    db.session.commit()

# Delete Suggestion
def delete_suggestion(suggestion_id):
    suggestion = Suggestion.query.get_or_404(suggestion_id)
    db.session.delete(suggestion)
    db.session.commit()

# Delete Moving Details (Announcement)
def delete_moving_details(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    db.session.delete(announcement)
    db.session.commit()

# Delete Party Hall Booking
def delete_booking(booking_id):
    booking = PartyHallBooking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()

# Insert Admin Announcement
def insert_admin_announcement(apartment_number, content, image_path=None):
    announcement = AdminAnnouncement(apartment_number=apartment_number, content=content,image_path=image_path)
    db.session.add(announcement)
    db.session.commit()

# Get all Admin Announcements
def get_all_admin_announcements():
    return AdminAnnouncement.query.order_by(AdminAnnouncement.timestamp.desc()).all()

def update_booking(booking_id, date, slot, payment, comments):
    booking = PartyHallBooking.query.get_or_404(booking_id)
    booking.date = date
    booking.slot = slot
    booking.payment = payment
    booking.comments = comments
    db.session.commit()

def is_booking_owned_by_user(booking_id, apartment_number):
    booking = PartyHallBooking.query.get(booking_id)
    return booking and booking.apartment_number == apartment_number
