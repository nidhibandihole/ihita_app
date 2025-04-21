from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from datetime import datetime
import hashlib
import os
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import imghdr
import re
from models import db, get_all_admin_announcements, is_booking_owned_by_user,insert_user, get_user_by_username,get_all_bookings, insert_booking, is_date_booked, insert_suggestion, get_all_suggestions, get_bookings_by_date, get_all_moving_details, get_moving_details_by_apartment, insert_moving_details, insert_admin_announcement, get_user_by_apartment_number, delete_booking, update_booking, get_all_staff_contacts
from flask_sqlalchemy import SQLAlchemy 
from sqlalchemy.exc import SQLAlchemyError
from models import PartyHallBooking, Announcement, StaffContact, AdminAnnouncement,Suggestion
# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Bind SQLAlchemy to app
db.init_app(app)

@app.context_processor
def inject_user_functions():
    return dict(
        get_user_by_username=get_user_by_username,
        is_admin=lambda: get_user_by_username(session.get('username', '')).is_admin if session.get('username') else False
    )

@app.route('/')
def index():
    return render_template('index.html')

def is_valid_apartment_number(apartment_number):
    # Define the valid apartment number pattern (3-digit numbers)
    pattern = r"^\d{3}$"
    
    # Create a list of valid apartment numbers including 000 to 415
    valid_apartments = ['000','001', '002', '003', '004', '005', '006', '007', '008', '009', '010', '011', '012', '013', '014', '015',
'101', '102', '103', '104', '105', '106', '107', '108', '109', '110', '111', '112', '113', '114', '115',
'201', '202', '203', '204', '205', '206', '207', '208', '209', '210', '211', '212', '213', '214', '215',
'301', '302', '303', '304', '305', '306', '307', '308', '309', '310', '311', '312', '313', '314', '315',
'401', '402', '403', '404', '405', '406', '407', '408', '409', '410', '411', '412', '413', '414', '415']
    
    # Return whether the apartment number is in the valid list and matches the pattern
    return apartment_number in valid_apartments and re.match(pattern, apartment_number)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        apartment_number = request.form['apartmentNumber'].upper().strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Confirm password check
        if password != confirm_password:
            flash("Passwords do not match. Please try again.", 'error')
            return redirect(url_for('signup'))

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Validate apartment number
        if not is_valid_apartment_number(apartment_number):
            flash("Invalid apartment number.", 'error')
            return redirect(url_for('signup'))

        # Username taken check
        if get_user_by_username(username):
            flash("Username already taken. Please choose another.", 'error')
            return redirect(url_for('signup'))

        # Apartment already registered check
        if get_user_by_apartment_number(apartment_number):
            flash("This apartment number is already registered.", 'error')
            return redirect(url_for('signup'))

        insert_user(username, hashed_password, apartment_number)
        flash("Signup successful! Please log in.", 'success')
        return redirect(url_for('signin'))

    return render_template('signup.html')



@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        user = get_user_by_username(username)

        if user and user.password == password:
            session['user_id'] = user.id
            session['username'] = user.username
            session['apartment_number'] = user.apartment_number
    
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.")
            return redirect(url_for('signin'))

    return render_template('signin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/make_announcements', methods=['GET', 'POST'])
def make_announcements():
    # Authentication check
    if 'username' not in session:
        flash("Please log in to continue.", 'error')
        return redirect(url_for('signin'))

    # Admin check
    user = get_user_by_username(session['username'])
    if not user or not user.is_admin:
        flash("Association admin access required.", 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Handle delete request
        if 'delete_id' in request.form:
            try:
                announcement = AdminAnnouncement.query.get_or_404(request.form['delete_id'])
                
                # Delete associated image file if exists
                if announcement.image_path:
                    try:
                        image_path = os.path.join(app.root_path, announcement.image_path)
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    except Exception as e:
                        app.logger.error(f"Error deleting image: {str(e)}")
                        flash("Error deleting announcement image.", 'error')
                
                # Delete from database
                db.session.delete(announcement)
                db.session.commit()
                flash("Announcement deleted successfully!", 'success')
                return redirect(url_for('make_announcements'))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error deleting announcement: {str(e)}")
                flash("Failed to delete announcement.", 'error')
                return redirect(url_for('make_announcements'))

        # Handle create announcement request
        content = request.form.get('content', '').strip()
        if not content:
            flash("Announcement content cannot be empty.", 'error')
            return redirect(url_for('make_announcements'))

        # Image processing
        image_path = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename != '':
                try:
                    # Validate image
                    filename = secure_filename(image_file.filename)
                    if not filename:
                        flash("Invalid image filename.", 'error')
                        return redirect(url_for('make_announcements'))

                    # Verify actual image file
                    file_stream = image_file.stream
                    if imghdr.what(file_stream) is None:
                        flash("Invalid image file.", 'error')
                        return redirect(url_for('make_announcements'))
                    file_stream.seek(0)  # Reset stream position

                    # Process image
                    img = Image.open(file_stream)
                    
                    # Resize (max 1200px width/height, maintain aspect ratio)
                    img.thumbnail((1200, 1200))
                    
                    # Prepare save
                    upload_dir = os.path.join(app.root_path, 'static', 'uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    full_path = os.path.join(upload_dir, filename)
                    
                    # Save with quality compression (85%)
                    img.save(full_path, quality=85, optimize=True)
                    
                    # Store web-compatible path
                    image_path = f"static/uploads/{filename}"

                except Exception as e:
                    app.logger.error(f"Image processing error: {str(e)}")
                    flash("Error processing image.", 'error')
                    return redirect(url_for('make_announcements'))

        # Save announcement
        try:
            new_announcement = AdminAnnouncement(
                apartment_number=user.apartment_number,
                content=content,
                image_path=image_path
            )
            db.session.add(new_announcement)
            db.session.commit()
            flash("Announcement posted successfully!", 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Database error: {str(e)}")
            flash("Failed to save announcement.", 'error')
            return redirect(url_for('make_announcements'))

    # GET request - show all announcements
    announcements = AdminAnnouncement.query.order_by(AdminAnnouncement.timestamp.desc()).all()
    return render_template('make_announcements.html',
                         admin_announcements=announcements,
                         is_admin=user.is_admin if user else False)
@app.route('/home')
def home():
    if 'user_id' in session:
        admin_announcements = get_all_admin_announcements()
        return render_template('home.html', username=session['username'], admin_announcements=admin_announcements)
    else:
        flash("Please log in to access the home page.")
        return redirect(url_for('signin'))
   

@app.route('/move_details_form', methods=['GET', 'POST'])
def move_details_form():
    if 'user_id' not in session:
        flash("Please log in to update your moving details.")
        return redirect(url_for('signin'))

    if request.method == 'POST':
        apartment_number = session['apartment_number']
        move_type = request.form['move_type']
        moving_date = request.form['moving_date']
        dues_clear = request.form['dues_clear']
        comments = request.form['comments']

        # Logic to update the moving details in the database
        insert_moving_details(apartment_number, move_type, moving_date, dues_clear, comments)
        flash("Moving details updated successfully!")
        return redirect(url_for('moving_details'))

    return render_template('move_details_form.html')



@app.route('/moving_details', methods=['GET', 'POST'])
def moving_details():
    if 'user_id' not in session:
        flash("Please log in to view or update your moving details.")
        return redirect(url_for('signin'))

    apartment_number = session['apartment_number']
    # Fetch moving details from the database
    moving_details = get_moving_details_by_apartment(apartment_number)  # Fetch logic from your DB

    return render_template('moving_details.html', moving_details=moving_details)


@app.route('/party_hall', methods=['GET', 'POST'])
def party_hall():
    if 'user_id' not in session:
        flash("Please log in to access the Party Hall log.")
        return redirect(url_for('signin'))

    if request.method == 'POST':
        apartment_number = session['apartment_number']
        date_str = request.form['date']
        slot = request.form['slot']
        payment = request.form['payment']
        comments = request.form.get('comments')

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = datetime.today().date()

            if date_obj < today:
                flash("You cannot book a past date.")
            else:
                if is_date_booked(date_obj):
                    existing_bookings = get_bookings_by_date(date_obj)

                    if slot == "Full Day":
                        if any(b.slot == "Full Day" for b in existing_bookings):
                            flash("A full day booking already exists for this date.")
                        elif any(b.slot in ["First Half", "Second Half"] for b in existing_bookings):
                            flash("You cannot book a full day when first or second half is already booked.")
                        else:
                            try:
                                insert_booking(apartment_number, date_obj, slot, payment, comments)
                                flash("Party hall booked successfully!")
                            except SQLAlchemyError as e:
                                print("Error while inserting booking:", e)
                                flash("Something went wrong while saving your booking. Please try again.")
                    elif slot in ["First Half", "Second Half"]:
                        if any(b.slot == "Full Day" for b in existing_bookings):
                            flash("You cannot book the first/second half when a full day is already booked.")
                        elif any(b.slot == "First Half" and slot == "Second Half" for b in existing_bookings):
                            flash("You cannot book both first and second half on the same day.")
                        elif any(b.slot == "Second Half" and slot == "First Half" for b in existing_bookings):
                            flash("You cannot book both first and second half on the same day.")
                        else:
                            try:
                                insert_booking(apartment_number, date_obj, slot, payment, comments)
                                flash("Party hall booked successfully!")
                            except SQLAlchemyError as e:
                                print("Error while inserting booking:", e)
                                flash("Something went wrong while saving your booking. Please try again.")
                else:
                    try:
                        insert_booking(apartment_number, date_obj, slot, payment, comments)
                        flash("Party hall booked successfully!")
                    except SQLAlchemyError as e:
                        print("Error while inserting booking:", e)
                        flash("Something went wrong while saving your booking. Please try again.")
        except ValueError:
            flash("Invalid date format.")

    bookings = get_all_bookings()
    return render_template('party_hall.html', bookings=bookings)

@app.route('/delete_booking/<int:booking_id>', methods=['POST', 'GET'])
def delete_booking_route(booking_id):
    if not is_booking_owned_by_user(booking_id, session['apartment_number']):
        flash("You are not authorized to delete this booking.")
        return redirect(url_for('party_hall'))

    delete_booking(booking_id)
    flash("Booking deleted successfully.")
    return redirect(url_for('party_hall'))

@app.route('/edit_moving_details/<int:announcement_id>', methods=['GET', 'POST'])
def edit_moving_details(announcement_id):
    if 'user_id' not in session:
        flash("Please log in to edit your moving details.")
        return redirect(url_for('signin'))

    # Fetch the existing moving details
    moving_detail = Announcement.query.get_or_404(announcement_id)

    # Check if the logged-in user is the owner of the moving details
    if moving_detail.apartment_number != session['apartment_number']:
        flash("You can only edit your own moving details.")
        return redirect(url_for('moving_details'))

    if request.method == 'POST':
        # Get updated details from the form
        moving_detail.move_type = request.form['move_type']
        moving_detail.moving_date = datetime.strptime(request.form['moving_date'], '%Y-%m-%d')
        moving_detail.dues_clear = request.form['dues_clear']
        moving_detail.comments = request.form['comments']

        # Commit changes to the database
        db.session.commit()
        flash("Moving details updated successfully!")
        return redirect(url_for('moving_details'))

    return render_template('move_details_form.html', moving_detail=moving_detail)

@app.route('/delete_moving_details/<int:announcement_id>', methods=['GET'])
def delete_moving_details(announcement_id):
    if 'user_id' not in session:
        flash("Please log in to delete your moving details.")
        return redirect(url_for('signin'))

    # Fetch the moving detail
    moving_detail = Announcement.query.get_or_404(announcement_id)

    # Check if the logged-in user is the owner of the moving details
    if moving_detail.apartment_number != session['apartment_number']:
        flash("You can only delete your own moving details.")
        return redirect(url_for('moving_details'))

    # Delete the moving detail
    db.session.delete(moving_detail)
    db.session.commit()
    flash("Moving details deleted successfully!")
    return redirect(url_for('moving_details'))


@app.route('/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
def edit_booking_route(booking_id):
    booking = PartyHallBooking.query.get_or_404(booking_id)

    if booking.apartment_number != session['apartment_number']:
        flash("Unauthorized access.")
        return redirect(url_for('party_hall'))

    if request.method == 'POST':
        try:
            new_date = datetime.strptime(request.form['date'], "%Y-%m-%d").date()
            new_slot = request.form['slot']
            new_payment = request.form['payment']
            new_comments = request.form.get('comments')

            today = datetime.today().date()

            # Check if the new booking date is in the past
            if new_date < today:
                flash("You cannot edit to a past date.")
                return redirect(url_for('party_hall'))

            # Get all existing bookings for the new date, excluding the current booking
            existing_bookings = get_bookings_by_date(new_date)

            # Remove the current booking from the existing bookings (do not consider it as a conflict)
            existing_bookings = [b for b in existing_bookings if b.id != booking_id]

            # Handle conflicts for Full Day bookings
            if new_slot == "Full Day":
                if any(b.slot == "Full Day" for b in existing_bookings):
                    flash("A full day booking already exists for this date.")
                    return redirect(url_for('party_hall'))
                elif any(b.slot in ["First Half", "Second Half"] for b in existing_bookings):
                    flash("You cannot book a full day when first or second half is already booked.")
                    return redirect(url_for('party_hall'))
            
            # Handle conflicts for Half Day bookings
            elif new_slot in ["First Half", "Second Half"]:
                if any(b.slot == "Full Day" for b in existing_bookings):
                    flash("You cannot book the first/second half when a full day is already booked.")
                    return redirect(url_for('party_hall'))
                elif any(b.slot == "First Half" and new_slot == "Second Half" for b in existing_bookings):
                    flash("You cannot book both first and second half on the same day.")
                    return redirect(url_for('party_hall'))
                elif any(b.slot == "Second Half" and new_slot == "First Half" for b in existing_bookings):
                    flash("You cannot book both first and second half on the same day.")
                    return redirect(url_for('party_hall'))

            # If no conflicts, proceed with updating the booking
            try:
                update_booking(booking_id, new_date, new_slot, new_payment, new_comments)
                flash("Booking updated successfully.")
                return redirect(url_for('party_hall'))
            except SQLAlchemyError as e:
                print("Error while updating booking:", e)
                flash("Something went wrong while updating your booking. Please try again.")
        
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.")

    return render_template('edit_booking.html', booking=booking)

@app.route('/important_contacts')
def important_contacts():
    if 'user_id' not in session:
        flash("Please log in to view contacts.", 'error')
        return redirect(url_for('signin'))

    user = get_user_by_username(session['username'])
    # Check if user is admin with specific criteria
    is_admin = user and user.username == 'admin' and user.apartment_number == '000' 
    contacts = get_all_staff_contacts()
    return render_template('contact_details.html', contacts=contacts, is_admin=is_admin)

@app.route('/add_contact', methods=['GET', 'POST'])
def add_contact():
    if 'username' not in session:
        flash("Please log in to continue.", 'error')
        return redirect(url_for('signin'))

    user = get_user_by_username(session['username'])
    if not user or user.username != 'admin' or user.apartment_number != '000' or user.is_admin != 1:
        flash("Access denied. Admins only.", 'error')
        return redirect(url_for('important_contacts'))

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        phone = request.form['phone']

        new_contact = StaffContact(name=name, role=role, phone=phone)
        db.session.add(new_contact)
        db.session.commit()
        flash('Contact added successfully!', 'success')
        return redirect(url_for('important_contacts'))

    return render_template('add_contact.html')

@app.route('/edit_contact/<int:contact_id>', methods=['GET', 'POST'])
def edit_contact(contact_id):
    if 'username' not in session:
        flash("Please log in to continue.", 'error')
        return redirect(url_for('signin'))

    user = get_user_by_username(session['username'])
    if not user or user.username != 'admin' or user.apartment_number != '000' or user.is_admin != 1:
        flash("Access denied. Admins only.", 'error')
        return redirect(url_for('important_contacts'))

    contact = StaffContact.query.get_or_404(contact_id)
    if request.method == 'POST':
        contact.name = request.form['name']
        contact.role = request.form['role']
        contact.phone = request.form['phone']
        db.session.commit()
        flash('Contact updated successfully!', 'success')
        return redirect(url_for('important_contacts'))

    return render_template('edit_contact.html', contact=contact)

@app.route('/delete_contact/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    if 'username' not in session:
        flash("Please log in to continue.", 'error')
        return redirect(url_for('signin'))

    user = get_user_by_username(session['username'])
    if not user or user.username != 'admin' or user.apartment_number != '000' or user.is_admin != 1:
        flash("Access denied. Admins only.", 'error')
        return redirect(url_for('important_contacts'))

    contact = StaffContact.query.get_or_404(contact_id)
    db.session.delete(contact)
    db.session.commit()
    flash('Contact deleted successfully.', 'success')
    return redirect(url_for('important_contacts'))


@app.route('/make_suggestion', methods=['GET', 'POST'])
def make_suggestion():
    # Authentication check
    if 'username' not in session:
        flash("Please log in to continue.", 'error')
        return redirect(url_for('signin'))

    user = get_user_by_username(session['username'])
    
    if request.method == 'POST':
        # Handle delete request
        if 'delete_id' in request.form:
            if not user or not user.is_admin:
                flash("Admin access required.", 'error')
                return redirect(url_for('make_suggestion'))
            
            try:
                suggestion = Suggestion.query.get_or_404(request.form['delete_id'])
                
                # Delete associated image if exists
                if suggestion.image_path:
                    try:
                        image_path = os.path.join(app.root_path, suggestion.image_path)
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    except Exception as e:
                        app.logger.error(f"Error deleting suggestion image: {str(e)}")
                
                db.session.delete(suggestion)
                db.session.commit()
                flash("Suggestion deleted successfully!", 'success')
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error deleting suggestion: {str(e)}")
                flash("Failed to delete suggestion.", 'error')
            return redirect(url_for('make_suggestion'))

        # Handle suggestion submission
        content = request.form.get('content', '').strip()
        if not content:
            flash("Suggestion cannot be empty.", 'error')
            return redirect(url_for('make_suggestion'))

        # Image processing
        image_path = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename != '':
                try:
                    filename = secure_filename(image_file.filename)
                    if not filename:
                        flash("Invalid image filename.", 'error')
                        return redirect(url_for('make_suggestion'))

                    file_stream = image_file.stream
                    if imghdr.what(file_stream) is None:
                        flash("Invalid image file.", 'error')
                        return redirect(url_for('make_suggestion'))
                    file_stream.seek(0)

                    img = Image.open(file_stream)
                    img.thumbnail((1200, 1200))
                    
                    upload_dir = os.path.join(app.root_path, 'static', 'uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    full_path = os.path.join(upload_dir, filename)
                    
                    img.save(full_path, quality=85, optimize=True)
                    image_path = f"static/uploads/{filename}"

                except Exception as e:
                    app.logger.error(f"Image processing error: {str(e)}")
                    flash("Error processing image.", 'error')
                    return redirect(url_for('make_suggestion'))

        try:
            new_suggestion = Suggestion(
                apartment_number=user.apartment_number,
                content=content,
                image_path=image_path
            )
            db.session.add(new_suggestion)
            db.session.commit()
            flash("Suggestion submitted successfully!", 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Database error: {str(e)}")
            flash("Failed to save suggestion.", 'error')
        
        return redirect(url_for('make_suggestion'))

    # GET request - show all suggestions
    suggestions = Suggestion.query.order_by(Suggestion.timestamp.desc()).all()
    return render_template('make_suggestion.html',
                         suggestions=suggestions,
                         is_admin=user.is_admin if user else False)

@app.route('/contact_details')
def contact_details():
    return render_template('contact_details.html')



if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)
