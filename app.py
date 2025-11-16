from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
import hashlib
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.config.from_object('config.Config')

# Database connection with better error handling
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            autocommit=True
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        flash('Database connection error!', 'danger')
        return None

# Role-based access control decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') not in ['admin', 'manager']:
            flash('Manager access required!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def analyst_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') not in ['admin', 'manager', 'analyst']:
            flash('Analyst access required!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'manager':
            return redirect(url_for('manager_dashboard'))
        elif role == 'analyst':
            return redirect(url_for('analyst_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM User WHERE username = %s AND password_hash = %s", 
                             (username, password_hash))
                user = cursor.fetchone()
                cursor.close()
                
                if user:
                    session['user_id'] = user['user_id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    flash('Login successful!', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Invalid credentials!', 'danger')
            except Error as e:
                flash(f'Database error: {e}', 'danger')
            finally:
                conn.close()
        else:
            flash('Database connection error!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    if not conn:
        return render_template('admin/dashboard.html', error="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get statistics
        cursor.execute("SELECT COUNT(*) as total_hotels FROM Hotel")
        total_hotels = cursor.fetchone()['total_hotels']
        
        cursor.execute("SELECT COUNT(*) as total_rooms FROM Room")
        total_rooms = cursor.fetchone()['total_rooms']
        
        cursor.execute("SELECT COUNT(*) as total_guests FROM Guest")
        total_guests = cursor.fetchone()['total_guests']
        
        cursor.execute("SELECT COUNT(*) as total_staff FROM Staff")
        total_staff = cursor.fetchone()['total_staff']
        
        cursor.close()
        
        return render_template('admin/dashboard.html', 
                             total_hotels=total_hotels,
                             total_rooms=total_rooms,
                             total_guests=total_guests,
                             total_staff=total_staff)
                             
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('admin/dashboard.html', error=str(e))
    finally:
        conn.close()

# Hotels Management
@app.route('/admin/hotels')
@admin_required
def admin_hotels():
    conn = get_db_connection()
    if not conn:
        return render_template('admin/hotels.html', hotels=[], error="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Hotel ORDER BY created_at DESC")
        hotels = cursor.fetchall()
        cursor.close()
        return render_template('admin/hotels.html', hotels=hotels)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('admin/hotels.html', hotels=[], error=str(e))
    finally:
        conn.close()

@app.route('/admin/hotels/add', methods=['POST'])
@admin_required
def add_hotel():
    hotel_name = request.form['hotel_name']
    address = request.form['address']
    city = request.form['city']
    country = request.form['country']
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Hotel (hotel_name, address, city, country) VALUES (%s, %s, %s, %s)",
                           (hotel_name, address, city, country))
            conn.commit()
            cursor.close()
            flash('Hotel added successfully!', 'success')
        except Error as e:
            flash(f'Error adding hotel: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_hotels'))

@app.route('/admin/hotels/edit/<int:hotel_id>', methods=['POST'])
@admin_required
def edit_hotel(hotel_id):
    hotel_name = request.form['hotel_name']
    address = request.form['address']
    city = request.form['city']
    country = request.form['country']
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE Hotel SET hotel_name=%s, address=%s, city=%s, country=%s WHERE hotel_id=%s",
                           (hotel_name, address, city, country, hotel_id))
            conn.commit()
            cursor.close()
            flash('Hotel updated successfully!', 'success')
        except Error as e:
            flash(f'Error updating hotel: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_hotels'))

@app.route('/admin/hotels/delete/<int:hotel_id>')
@admin_required
def delete_hotel(hotel_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Hotel WHERE hotel_id = %s", (hotel_id,))
            conn.commit()
            cursor.close()
            flash('Hotel deleted successfully!', 'success')
        except Error as e:
            flash(f'Error deleting hotel: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_hotels'))

# Rooms Management
@app.route('/admin/rooms')
@admin_required
def admin_rooms():
    conn = get_db_connection()
    if not conn:
        return render_template('admin/rooms.html', rooms=[], hotels=[], error="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.*, h.hotel_name 
            FROM Room r 
            JOIN Hotel h ON r.hotel_id = h.hotel_id 
            ORDER BY r.created_at DESC
        """)
        rooms = cursor.fetchall()
        cursor.execute("SELECT * FROM Hotel")
        hotels = cursor.fetchall()
        cursor.close()
        return render_template('admin/rooms.html', rooms=rooms, hotels=hotels)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('admin/rooms.html', rooms=[], hotels=[], error=str(e))
    finally:
        conn.close()

@app.route('/admin/rooms/add', methods=['POST'])
@admin_required
def add_room():
    hotel_id = request.form['hotel_id']
    room_number = request.form['room_number']
    room_type = request.form['room_type']
    price_per_night = request.form['price_per_night']
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Room (hotel_id, room_number, room_type, price_per_night) 
                VALUES (%s, %s, %s, %s)
            """, (hotel_id, room_number, room_type, price_per_night))
            conn.commit()
            cursor.close()
            flash('Room added successfully!', 'success')
        except Error as e:
            flash(f'Error adding room: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_rooms'))

@app.route('/admin/rooms/edit/<int:room_id>', methods=['POST'])
@admin_required
def edit_room(room_id):
    hotel_id = request.form['hotel_id']
    room_number = request.form['room_number']
    room_type = request.form['room_type']
    price_per_night = request.form['price_per_night']
    status = request.form['status']
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Room 
                SET hotel_id=%s, room_number=%s, room_type=%s, price_per_night=%s, status=%s 
                WHERE room_id=%s
            """, (hotel_id, room_number, room_type, price_per_night, status, room_id))
            conn.commit()
            cursor.close()
            flash('Room updated successfully!', 'success')
        except Error as e:
            flash(f'Error updating room: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_rooms'))

@app.route('/admin/rooms/delete/<int:room_id>')
@admin_required
def delete_room(room_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Room WHERE room_id = %s", (room_id,))
            conn.commit()
            cursor.close()
            flash('Room deleted successfully!', 'success')
        except Error as e:
            flash(f'Error deleting room: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_rooms'))

# Guests Management
@app.route('/admin/guests')
@admin_required
def admin_guests():
    conn = get_db_connection()
    if not conn:
        return render_template('admin/guests.html', guests=[], error="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Guest ORDER BY created_at DESC")
        guests = cursor.fetchall()
        cursor.close()
        return render_template('admin/guests.html', guests=guests)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('admin/guests.html', guests=[], error=str(e))
    finally:
        conn.close()

@app.route('/admin/guests/add', methods=['POST'])
@admin_required
def add_guest():
    guest_name = request.form['guest_name']
    email = request.form['email']
    phone = request.form['phone']
    password = request.form['password']
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Guest (guest_name, email, phone, password_hash) 
                VALUES (%s, %s, %s, %s)
            """, (guest_name, email, phone, password_hash))
            conn.commit()
            cursor.close()
            flash('Guest added successfully!', 'success')
        except Error as e:
            flash(f'Error adding guest: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_guests'))

@app.route('/admin/guests/edit/<int:guest_id>', methods=['POST'])
@admin_required
def edit_guest(guest_id):
    guest_name = request.form['guest_name']
    email = request.form['email']
    phone = request.form['phone']
    password = request.form.get('password')
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            if password:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                cursor.execute("""
                    UPDATE Guest 
                    SET guest_name=%s, email=%s, phone=%s, password_hash=%s 
                    WHERE guest_id=%s
                """, (guest_name, email, phone, password_hash, guest_id))
            else:
                cursor.execute("""
                    UPDATE Guest 
                    SET guest_name=%s, email=%s, phone=%s 
                    WHERE guest_id=%s
                """, (guest_name, email, phone, guest_id))
            conn.commit()
            cursor.close()
            flash('Guest updated successfully!', 'success')
        except Error as e:
            flash(f'Error updating guest: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_guests'))

@app.route('/admin/guests/delete/<int:guest_id>')
@admin_required
def delete_guest(guest_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Guest WHERE guest_id = %s", (guest_id,))
            conn.commit()
            cursor.close()
            flash('Guest deleted successfully!', 'success')
        except Error as e:
            flash(f'Error deleting guest: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_guests'))

# Staff Management
@app.route('/admin/staff')
@admin_required
def admin_staff():
    conn = get_db_connection()
    if not conn:
        return render_template('admin/staff.html', staff_list=[], hotels=[], error="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, h.hotel_name 
            FROM Staff s 
            LEFT JOIN Hotel h ON s.hotel_id = h.hotel_id 
            ORDER BY s.created_at DESC
        """)
        staff_list = cursor.fetchall()
        
        cursor.execute("SELECT * FROM Hotel")
        hotels = cursor.fetchall()
        
        cursor.close()
        return render_template('admin/staff.html', staff_list=staff_list, hotels=hotels)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('admin/staff.html', staff_list=[], hotels=[], error=str(e))
    finally:
        conn.close()

@app.route('/admin/staff/add', methods=['POST'])
@admin_required
def add_staff():
    staff_name = request.form['staff_name']
    role = request.form['role']
    email = request.form['email']
    hotel_id = request.form.get('hotel_id') or None
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Staff (staff_name, role, email, hotel_id) 
                VALUES (%s, %s, %s, %s)
            """, (staff_name, role, email, hotel_id))
            conn.commit()
            cursor.close()
            flash('Staff member added successfully!', 'success')
        except Error as e:
            flash(f'Error adding staff: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_staff'))

@app.route('/admin/staff/edit/<int:staff_id>', methods=['POST'])
@admin_required
def edit_staff(staff_id):
    staff_name = request.form['staff_name']
    role = request.form['role']
    email = request.form['email']
    hotel_id = request.form.get('hotel_id') or None
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Staff 
                SET staff_name=%s, role=%s, email=%s, hotel_id=%s 
                WHERE staff_id=%s
            """, (staff_name, role, email, hotel_id, staff_id))
            conn.commit()
            cursor.close()
            flash('Staff member updated successfully!', 'success')
        except Error as e:
            flash(f'Error updating staff: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_staff'))

@app.route('/admin/staff/delete/<int:staff_id>')
@admin_required
def delete_staff(staff_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Staff WHERE staff_id = %s", (staff_id,))
            conn.commit()
            cursor.close()
            flash('Staff member deleted successfully!', 'success')
        except Error as e:
            flash(f'Error deleting staff: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('admin_staff'))

# ============================================================================
# MANAGER ROUTES
# ============================================================================

@app.route('/manager/dashboard')
@manager_required
def manager_dashboard():
    conn = get_db_connection()
    if not conn:
        return render_template('manager/dashboard.html', error="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as total_reservations FROM Reservation")
        total_reservations = cursor.fetchone()['total_reservations']
        
        cursor.execute("SELECT COUNT(*) as active_reservations FROM Reservation WHERE booking_status = 'Active'")
        active_reservations = cursor.fetchone()['active_reservations']
        
        cursor.execute("SELECT SUM(billed_amount) as total_revenue FROM Billing WHERE billing_status = 'Paid'")
        total_revenue = cursor.fetchone()['total_revenue'] or 0
        
        cursor.close()
        
        return render_template('manager/dashboard.html',
                             total_reservations=total_reservations,
                             active_reservations=active_reservations,
                             total_revenue=total_revenue)
                             
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('manager/dashboard.html', error=str(e))
    finally:
        conn.close()

@app.route('/manager/reservations')
@manager_required
def manager_reservations():
    conn = get_db_connection()
    if not conn:
        return render_template('manager/reservations.html', reservations=[], guests=[], rooms=[], error="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.*, g.guest_name, rm.room_number, h.hotel_name
            FROM Reservation r
            JOIN Guest g ON r.guest_id = g.guest_id
            JOIN Room rm ON r.room_id = rm.room_id
            JOIN Hotel h ON rm.hotel_id = h.hotel_id
            ORDER BY r.created_at DESC
        """)
        reservations = cursor.fetchall()
        
        cursor.execute("SELECT * FROM Guest")
        guests = cursor.fetchall()
        
        cursor.execute("SELECT * FROM Room WHERE status = 'Available'")
        rooms = cursor.fetchall()
        
        cursor.close()
        
        return render_template('manager/reservations.html', 
                             reservations=reservations, 
                             guests=guests, 
                             rooms=rooms)
                             
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('manager/reservations.html', reservations=[], guests=[], rooms=[], error=str(e))
    finally:
        conn.close()

@app.route('/manager/reservations/add', methods=['POST'])
@manager_required
def add_reservation():
    guest_id = request.form['guest_id']
    room_id = request.form['room_id']
    check_in_date = request.form['check_in_date']
    check_out_date = request.form['check_out_date']
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Add reservation
            cursor.execute("""
                INSERT INTO Reservation (guest_id, room_id, check_in_date, check_out_date) 
                VALUES (%s, %s, %s, %s)
            """, (guest_id, room_id, check_in_date, check_out_date))
            
            reservation_id = cursor.lastrowid
            
            # Update room status
            cursor.execute("UPDATE Room SET status = 'Booked' WHERE room_id = %s", (room_id,))
            
            # Calculate and add billing
            cursor.execute("SELECT price_per_night FROM Room WHERE room_id = %s", (room_id,))
            room_price = cursor.fetchone()[0]
            
            check_in = datetime.strptime(check_in_date, '%Y-%m-%d')
            check_out = datetime.strptime(check_out_date, '%Y-%m-%d')
            nights = (check_out - check_in).days
            total_amount = room_price * nights
            
            cursor.execute("""
                INSERT INTO Billing (reservation_id, billed_amount) 
                VALUES (%s, %s)
            """, (reservation_id, total_amount))
            
            conn.commit()
            cursor.close()
            flash('Reservation added successfully!', 'success')
            
        except Error as e:
            flash(f'Error adding reservation: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('manager_reservations'))

@app.route('/manager/reservations/update_status/<int:reservation_id>', methods=['POST'])
@manager_required
def update_reservation_status(reservation_id):
    new_status = request.form['status']
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            cursor.execute("UPDATE Reservation SET booking_status = %s WHERE reservation_id = %s",
                           (new_status, reservation_id))
            
            # If checked out, mark room as available
            if new_status == 'CheckedOut':
                cursor.execute("""
                    UPDATE Room r 
                    JOIN Reservation res ON r.room_id = res.room_id 
                    SET r.status = 'Available' 
                    WHERE res.reservation_id = %s
                """, (reservation_id,))
            
            conn.commit()
            cursor.close()
            flash('Reservation status updated!', 'success')
            
        except Error as e:
            flash(f'Error updating reservation status: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('manager_reservations'))

@app.route('/manager/billing')
@manager_required
def manager_billing():
    conn = get_db_connection()
    if not conn:
        return render_template('manager/billing.html', billing=[], error="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, r.reservation_id, g.guest_name
            FROM Billing b
            JOIN Reservation r ON b.reservation_id = r.reservation_id
            JOIN Guest g ON r.guest_id = g.guest_id
            ORDER BY b.created_at DESC
        """)
        billing = cursor.fetchall()
        cursor.close()
        
        return render_template('manager/billing.html', billing=billing)
        
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('manager/billing.html', billing=[], error=str(e))
    finally:
        conn.close()

@app.route('/manager/billing/process_payment/<int:billing_id>', methods=['POST'])
@manager_required
def process_payment(billing_id):
    payment_amount = float(request.form['payment_amount'])
    payment_method = request.form['payment_method']
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get current billing info
            cursor.execute("SELECT * FROM Billing WHERE billing_id = %s", (billing_id,))
            billing = cursor.fetchone()
            
            if billing:
                new_paid_amount = billing['paid_amount'] + payment_amount
                new_paid_amount = round(new_paid_amount, 2)
                
                # Determine new status
                if new_paid_amount >= billing['billed_amount']:
                    new_status = 'Paid'
                elif new_paid_amount > 0:
                    new_status = 'Partial'
                else:
                    new_status = 'Unpaid'
                
                # Update billing
                cursor.execute("""
                    UPDATE Billing 
                    SET paid_amount = %s, billing_status = %s, payment_method = %s 
                    WHERE billing_id = %s
                """, (new_paid_amount, new_status, payment_method, billing_id))
                
                conn.commit()
                cursor.close()
                flash(f'Payment of ${payment_amount:.2f} processed successfully!', 'success')
            else:
                flash('Billing record not found!', 'danger')
                
        except Error as e:
            flash(f'Error processing payment: {e}', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('manager_billing'))

# ============================================================================
# ANALYST ROUTES
# ============================================================================

@app.route('/analyst/dashboard')
@analyst_required
def analyst_dashboard():
    conn = get_db_connection()
    if not conn:
        return render_template('analyst/dashboard.html', error="Database connection failed")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Revenue analytics
        cursor.execute("""
            SELECT 
                SUM(billed_amount) as total_revenue,
                SUM(paid_amount) as total_paid,
                AVG(billed_amount) as avg_booking_value,
                COUNT(*) as total_bookings
            FROM Billing
        """)
        revenue_stats = cursor.fetchone()
        
        # Room occupancy
        cursor.execute("""
            SELECT 
                room_type,
                COUNT(*) as total_rooms,
                SUM(CASE WHEN status = 'Booked' THEN 1 ELSE 0 END) as booked_rooms
            FROM Room 
            GROUP BY room_type
        """)
        occupancy_stats = cursor.fetchall()
        
        # Monthly revenue
        cursor.execute("""
            SELECT 
                DATE_FORMAT(b.created_at, '%Y-%m') as month,
                SUM(b.billed_amount) as revenue
            FROM Billing b
            WHERE b.billing_status = 'Paid'
            GROUP BY DATE_FORMAT(b.created_at, '%Y-%m')
            ORDER BY month DESC
            LIMIT 6
        """)
        monthly_revenue = cursor.fetchall()
        
        cursor.close()
        
        return render_template('analyst/dashboard.html',
                             revenue_stats=revenue_stats,
                             occupancy_stats=occupancy_stats,
                             monthly_revenue=monthly_revenue)
                             
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('analyst/dashboard.html', error=str(e))
    finally:
        conn.close()

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/available-rooms')
def api_available_rooms():
    hotel_id = request.args.get('hotel_id')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT r.*, h.hotel_name 
                FROM Room r 
                JOIN Hotel h ON r.hotel_id = h.hotel_id 
                WHERE r.status = 'Available'
            """
            params = []
            
            if hotel_id:
                query += " AND r.hotel_id = %s"
                params.append(hotel_id)
            
            cursor.execute(query, params)
            rooms = cursor.fetchall()
            cursor.close()
            
            return jsonify(rooms)
            
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()
    
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/api/room-price/<int:room_id>')
def api_room_price(room_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT price_per_night FROM Room WHERE room_id = %s", (room_id,))
            room = cursor.fetchone()
            cursor.close()
            
            if room:
                return jsonify({'price': room['price_per_night']})
            else:
                return jsonify({'error': 'Room not found'}), 404
                
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()
    
    return jsonify({'error': 'Database connection failed'}), 500

if __name__ == '__main__':
    app.run(debug=True)
