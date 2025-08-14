#Libraries needed to run our code
from flask import Flask, render_template, request, redirect, session, url_for, flash
import pymysql
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import md5

app = Flask(__name__)
app.secret_key = 'gaellehelin'

#Setting up our database connection
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='',
                       db='air_ticket_reservation_system', #The name of our database on MySQL
                       cursorclass=pymysql.cursors.DictCursor)

#Function to hash the customer/staff passwords
def hash_password(password):
    return md5(password.encode()).hexdigest()

#Initializing public home page route
@app.route('/')
def home():
    return render_template('home.html', flights=None)

# Page to show the registration form
@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

# Page to show the login form
@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

# Logs out the current user by clearing the session
@app.route('/logout')
def logout():
    session.clear()
    #flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# Customer routes
# Handles customer registration logic
@app.route('/register_customer', methods=['POST'])
def register_customer():
    try:
        # Collecting form data
        email = request.form['email']
        name = request.form['name']
        password = hash_password(request.form['password'])
        building_number = request.form['building_number']
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        phone_number = request.form['phone_number']
        passport_number = request.form['passport_number']
        passport_expiration = request.form['passport_expiration']
        passport_country = request.form['passport_country']
        date_of_birth = request.form['date_of_birth']

        with conn.cursor() as cursor:
            # Check for email conflict
            cursor.execute("SELECT * FROM Customer WHERE Email = %s", (email,))
            if cursor.fetchone():
                flash("Email is already registered.", "warning")
                return redirect(url_for('home'))

            # Insert new customer
            cursor.execute("""
                INSERT INTO Customer (Email, Name, Password, Building_number, Street, City, State, Phone_number,
                                      Passport_number, Passport_expiration, Passport_country, Date_of_birth)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (email, name, password, building_number, street, city, state, phone_number,
                  passport_number, passport_expiration, passport_country, date_of_birth))
            conn.commit()

        #flash("Registration successful. Please log in.", "success")
        return redirect(url_for('login'))

    except Exception as e:
        print("Customer registration error:", e)
        flash("An error occurred during registration.", "danger")
        return redirect(url_for('register'))

# Handles customer login and session management
@app.route('/customer_login', methods=['POST'])
def customer_login():
    try:
        email = request.form['customer_email']
        password = request.form['customer_password']
        hashed_password = hash_password(password)

        print("Login attempt for:", email)

        with conn.cursor() as cursor:
            # Check if customer exists with matching email and password
            query = "SELECT * FROM Customer WHERE Email = %s AND Password = %s"
            cursor.execute(query, (email, hashed_password))
            customer = cursor.fetchone()

            if customer:
                # Start session
                session['user_type'] = 'customer'
                session['email'] = customer['Email']
                session['customer_name'] = customer['Name']
                #flash('Login successful!', 'success')
                return redirect(url_for('customer_home'))
            else:
                flash('Invalid email or password. Please try again.', 'danger')
                return redirect(url_for('home'))

    except Exception as e:
        print("Error during login:", e)
        flash('An error occurred during login. Please try again later.', 'danger')
        return redirect(url_for('login'))

# Displays the customer home dashboard (after login)
@app.route('/customer_home')
def customer_home():
    if 'user_type' in session and session['user_type'] == 'customer':
        return render_template('customer_home.html', customer_name=session.get('customer_name'))
    else:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

# Shows all upcoming flights purchased by the logged-in customer
@app.route('/view_my_flights')
def view_my_flights():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash('Please log in to access your flights.', 'danger')
        return redirect(url_for('login'))

    customer_email = session['email']

    try:
        with conn.cursor() as cursor:
            query = """
                SELECT 
                    f.Flight_number AS flight_number,
                    f.Departure_airport_code AS source,
                    f.Arrival_airport_code AS destination,
                    f.Departure_date_time AS departure_time,
                    f.Arrival_date_time AS arrival_time,
                    f.Flight_status AS status
                FROM Ticket t
                JOIN Purchased_By pb ON t.Ticket_ID = pb.Ticket_ID
                JOIN Flight f ON t.Flight_number = f.Flight_number 
                             AND t.Departure_date_time = f.Departure_date_time
                             AND t.Airline_name = f.Airline_name
                WHERE pb.Customer_email = %s
                  AND f.Departure_date_time > NOW()
                ORDER BY f.Departure_date_time ASC
            """
            cursor.execute(query, (customer_email,))
            flights = cursor.fetchall()

        future_flights = []
        now = datetime.now()

        for flight in flights:
            departure_time = flight['departure_time']
            time_diff = departure_time - now

            flight['cancel_allowed'] = time_diff.total_seconds() > 86400  # 24 hours = 86400 seconds
            future_flights.append(flight)

        return render_template('view_my_flights.html', future_flights=future_flights)

    except Exception as e:
        print("Error fetching flights:", e)
        flash("An error occurred while retrieving your flights.", "danger")
        return redirect(url_for('customer_home'))

# Handles flight cancellation logic (only if >24h from departure)
@app.route('/cancel_flight', methods=['POST'])
def cancel_flight():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    flight_number = request.form['flight_number']
    customer_email = session['email']

    try:
        with conn.cursor() as cursor:
            # Find the ticket for this flight and customer
            cursor.execute("""
                SELECT t.Ticket_ID, f.Departure_date_time
                FROM Ticket t
                JOIN Purchased_By pb ON t.Ticket_ID = pb.Ticket_ID
                JOIN Flight f ON t.Flight_number = f.Flight_number AND t.Departure_date_time = f.Departure_date_time
                WHERE pb.Customer_email = %s AND t.Flight_number = %s AND f.Departure_date_time > NOW()
                LIMIT 1
            """, (customer_email, flight_number))

            ticket = cursor.fetchone()

            if not ticket:
                flash("Ticket not found or cannot be canceled.", "danger")
                return redirect(url_for('view_my_flights'))

            # Check if cancellation is allowed
            departure_time = ticket['Departure_date_time']
            if (departure_time - datetime.now()).total_seconds() <= 86400:
                flash("Cannot cancel flights within 24 hours of departure.", "warning")
                return redirect(url_for('customer_home'))

            # Delete from Purchased_By first due to FK constraints
            cursor.execute("DELETE FROM Purchased_By WHERE Ticket_ID = %s", (ticket['Ticket_ID'],))
            cursor.execute("DELETE FROM Ticket WHERE Ticket_ID = %s", (ticket['Ticket_ID'],))

            conn.commit()

        #flash("Your ticket has been successfully canceled.", "success")
        return redirect(url_for('view_my_flights'))

    except Exception as e:
        print("Error during cancellation:", e)
        flash("An error occurred while canceling your ticket.", "danger")
        return redirect(url_for('view_my_flights'))

# Allows customers to access the flight search page
@app.route('/customer_search_for_flights', methods=['GET'])
def customer_search_for_flights():
    if 'user_type' in session and session['user_type'] == 'customer':
        return render_template('search_for_flights.html')
    else:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

# Processes the search query for logged-in customers and applies dynamic pricing
@app.route('/search_for_flights_logged_in', methods=['POST'])
def search_for_flights_logged_in():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    try:
        source = request.form['source'].upper()
        destination = request.form['destination'].upper()
        departure_date = request.form['departure_date']
        trip_type = request.form['trip_type']
        return_date = request.form.get('return_date')  # Might be None

        with conn.cursor() as cursor:
            # Common filters for both types
            base_query = """
                SELECT 
                    f.Flight_number AS flight_number, 
                    f.Departure_airport_code AS source,
                    f.Arrival_airport_code AS destination,
                    f.Departure_date_time AS departure_time,
                    f.Arrival_date_time AS arrival_time,
                    f.Base_price AS base_price,
                    ap.Number_of_seats AS total_seats,
                    COUNT(t.Ticket_ID) AS booked_seats
                FROM Flight f
                JOIN Airplane ap ON f.Identification_number = ap.Identification_number AND f.Airplane_airline_name = ap.Airline_name
                LEFT JOIN Ticket t ON t.Flight_number = f.Flight_number AND t.Departure_date_time = f.Departure_date_time AND t.Airline_name = f.Airline_name
                WHERE f.Departure_airport_code = %s
                    AND f.Arrival_airport_code = %s
                    AND DATE(f.Departure_date_time) = %s
                    AND f.Departure_date_time > NOW()
                GROUP BY f.Flight_number, f.Departure_date_time, f.Airline_name
                HAVING (ap.Number_of_seats - COUNT(t.Ticket_ID)) > 0
            """
            
            cursor.execute(base_query, (source, destination, departure_date))
            departure_flights = cursor.fetchall()

            # Adjust prices based on occupancy
            for flight in departure_flights:
                booked_seats = flight['booked_seats']
                total_seats = flight['total_seats']
                occupancy_rate = booked_seats / total_seats if total_seats else 0
                if occupancy_rate >= 0.6:
                    flight['price'] = float(flight['base_price']) * 1.2
                else:
                    flight['price'] = float(flight['base_price'])

            return_flights = []

            if trip_type == 'round' and return_date:
                return_query = """
                    SELECT 
                        f.Flight_number AS flight_number, 
                        f.Departure_airport_code AS source,
                        f.Arrival_airport_code AS destination,
                        f.Departure_date_time AS departure_time,
                        f.Arrival_date_time AS arrival_time,
                        f.Base_price AS base_price,
                        ap.Number_of_seats AS total_seats,
                        COUNT(t.Ticket_ID) AS booked_seats
                    FROM Flight f
                    JOIN Airplane ap ON f.Identification_number = ap.Identification_number AND f.Airplane_airline_name = ap.Airline_name
                    LEFT JOIN Ticket t ON t.Flight_number = f.Flight_number AND t.Departure_date_time = f.Departure_date_time AND t.Airline_name = f.Airline_name
                    WHERE f.Departure_airport_code = %s
                        AND f.Arrival_airport_code = %s
                        AND DATE(f.Departure_date_time) = %s
                        AND f.Departure_date_time > NOW()
                        AND f.Departure_date_time > %s
                    GROUP BY f.Flight_number, f.Departure_date_time, f.Airline_name
                    HAVING (ap.Number_of_seats - COUNT(t.Ticket_ID)) > 0
                """
                cursor.execute(return_query, (destination, source, return_date, departure_date))
                return_flights = cursor.fetchall()

                for flight in return_flights:
                    booked_seats = flight['booked_seats']
                    total_seats = flight['total_seats']
                    occupancy_rate = booked_seats / total_seats if total_seats else 0
                    if occupancy_rate >= 0.6:
                        flight['price'] = float(flight['base_price']) * 1.2
                    else:
                        flight['price'] = float(flight['base_price'])

        return render_template(
            'search_for_flights.html',  # Keep the user on the same page
            departure_flights=departure_flights,
            return_flights=return_flights if trip_type == 'round' else None,
            trip_type=trip_type
        )

    except Exception as e:
        print("Error in flight search:", e)
        flash("An error occurred while searching for flights.", "danger")
        return redirect(url_for('customer_home'))

# Public version of search (used when not logged in)
@app.route('/search_for_flights', methods=['POST'])
def search_for_flights():
    try:
        source = request.form['source'].upper()
        destination = request.form['destination'].upper()
        departure_date = request.form['departure_date']
        trip_type = request.form['trip_type']
        return_date = request.form.get('return_date')  # Might be None

        with conn.cursor() as cursor:
            # Common filters for both types
            base_query = """
                SELECT 
                    f.Flight_number AS flight_number, 
                    f.Departure_airport_code AS source,
                    f.Arrival_airport_code AS destination,
                    f.Departure_date_time AS departure_time,
                    f.Arrival_date_time AS arrival_time,
                    f.Base_price AS base_price,
                    ap.Number_of_seats AS total_seats,
                    COUNT(t.Ticket_ID) AS booked_seats
                FROM Flight f
                JOIN Airplane ap ON f.Identification_number = ap.Identification_number AND f.Airplane_airline_name = ap.Airline_name
                LEFT JOIN Ticket t ON t.Flight_number = f.Flight_number AND t.Departure_date_time = f.Departure_date_time AND t.Airline_name = f.Airline_name
                WHERE f.Departure_airport_code = %s
                    AND f.Arrival_airport_code = %s
                    AND DATE(f.Departure_date_time) = %s
                    AND f.Departure_date_time > NOW()
                GROUP BY f.Flight_number, f.Departure_date_time, f.Airline_name
                HAVING (ap.Number_of_seats - COUNT(t.Ticket_ID)) > 0
            """

            cursor.execute(base_query, (source, destination, departure_date))
            departure_flights = cursor.fetchall()

            # Adjust prices based on occupancy
            for flight in departure_flights:
                booked_seats = flight['booked_seats']
                total_seats = flight['total_seats']
                occupancy_rate = booked_seats / total_seats if total_seats else 0
                if occupancy_rate >= 0.6:
                    flight['price'] = float(flight['base_price']) * 1.2
                else:
                    flight['price'] = float(flight['base_price'])

            return_flights = []

            if trip_type == 'round' and return_date:
                return_query = """
                    SELECT 
                        f.Flight_number AS flight_number, 
                        f.Departure_airport_code AS source,
                        f.Arrival_airport_code AS destination,
                        f.Departure_date_time AS departure_time,
                        f.Arrival_date_time AS arrival_time,
                        f.Base_price AS base_price,
                        ap.Number_of_seats AS total_seats,
                        COUNT(t.Ticket_ID) AS booked_seats
                    FROM Flight f
                    JOIN Airplane ap ON f.Identification_number = ap.Identification_number AND f.Airplane_airline_name = ap.Airline_name
                    LEFT JOIN Ticket t ON t.Flight_number = f.Flight_number AND t.Departure_date_time = f.Departure_date_time AND t.Airline_name = f.Airline_name
                    WHERE f.Departure_airport_code = %s
                        AND f.Arrival_airport_code = %s
                        AND DATE(f.Departure_date_time) = %s
                        AND f.Departure_date_time > NOW()
                        AND f.Departure_date_time > %s
                    GROUP BY f.Flight_number, f.Departure_date_time, f.Airline_name
                    HAVING (ap.Number_of_seats - COUNT(t.Ticket_ID)) > 0
                """
                cursor.execute(return_query, (destination, source, return_date, departure_date))
                return_flights = cursor.fetchall()

                for flight in return_flights:
                    booked_seats = flight['booked_seats']
                    total_seats = flight['total_seats']
                    occupancy_rate = booked_seats / total_seats if total_seats else 0
                    if occupancy_rate >= 0.6:
                        flight['price'] = float(flight['base_price']) * 1.2
                    else:
                        flight['price'] = float(flight['base_price'])

        return render_template(
            'home.html',
            departure_flights=departure_flights,
            return_flights=return_flights if trip_type == 'round' else None,
            trip_type=trip_type
        )

    except Exception as e:
        print("Error in flight search:", e)
        flash("An error occurred while searching for flights.", "danger")
        return redirect(url_for('home'))

# Displays ticket purchase page for a selected flight
@app.route('/customer_buy_ticket', methods=['POST'])
def customer_buy_ticket():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    flight_number = request.form['flight_number']
    
    with conn.cursor() as cursor:
        query = """
            SELECT 
                f.Flight_number AS flight_number,
                f.Departure_date_time AS departure_date_time,
                f.Arrival_date_time AS arrival_date_time,
                f.Airline_name AS airline_name,
                f.Airplane_airline_name AS airplane_airline_name,
                f.Identification_number AS identification_number,
                f.Departure_airport_code AS departure_airport_code,
                f.Arrival_airport_code AS arrival_airport_code,
                f.Base_price AS base_price
            FROM Flight f
            WHERE f.Flight_number = %s
            LIMIT 1
        """
        cursor.execute(query, (flight_number,))
        flight = cursor.fetchone()

        if not flight:
            flash("Flight not found.", "danger")
            return redirect(url_for('customer_home'))

        # Calculate dynamic price
        occupancy_query = """
            SELECT ap.Number_of_seats AS total_seats, COUNT(t.Ticket_ID) AS booked_seats
            FROM Flight f
            JOIN Airplane ap ON f.Identification_number = ap.Identification_number AND f.Airplane_airline_name = ap.Airline_name
            LEFT JOIN Ticket t ON t.Flight_number = f.Flight_number AND t.Departure_date_time = f.Departure_date_time AND t.Airline_name = f.Airline_name
            WHERE f.Flight_number = %s
            GROUP BY f.Flight_number
        """
        cursor.execute(occupancy_query, (flight_number,))
        occupancy = cursor.fetchone()

        occupancy_rate = occupancy['booked_seats'] / occupancy['total_seats'] if occupancy['total_seats'] else 0
        sold_price = flight['base_price'] * Decimal('1.2') if occupancy_rate >= 0.6 else flight['base_price']

    # Pass flight info and calculated price
    return render_template('buy_ticket.html', flight=flight, sold_price=sold_price)

# Finalizes ticket purchase and stores payment data
@app.route('/purchase_ticket', methods=['POST'])
def purchase_ticket():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    try:
        # Get flight & payment data
        flight_number = request.form['flight_number']
        departure_date_time = request.form['departure_date_time']
        airline_name = request.form['airline_name']
        sold_price = request.form['sold_price']

        card_type = request.form['card_type']
        card_number = request.form['card_number']
        name_on_card = request.form['name_on_card']
        expiration_month = request.form['expiration_date']  # "YYYY-MM"
        expiration_date = f"{expiration_month}-01"  # Convert to full DATE format
        security_code = request.form['security_code']

        # Simple payment validation (simulate real-world checks)
        if not (card_type and card_number.isdigit() and name_on_card and expiration_date):
            flash("Invalid payment details. Please check your input.", "danger")
            return redirect(url_for('customer_home'))

        with conn.cursor() as cursor:
            cursor.execute("SELECT CAST(SUBSTRING(Ticket_ID, 4) AS UNSIGNED) AS num FROM Ticket ORDER BY num")
            ticket_nums = cursor.fetchall()

            existing_numbers = [row['num'] for row in ticket_nums]

            next_ticket_number = 1
            for num in existing_numbers:
                if num == next_ticket_number:
                    next_ticket_number += 1
                else:
                    break

            ticket_id = f"TKT{next_ticket_number:03d}"

            # Insert ticket
            cursor.execute("""
                INSERT INTO Ticket (Ticket_ID, Flight_number, Departure_date_time, Airline_name, 
                                    Sold_price, Card_type, Card_number, Name_on_card, Expiration_date, 
                                    Purchase_date_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (ticket_id, flight_number, departure_date_time, airline_name, sold_price, 
                  card_type, card_number, name_on_card, expiration_date))

            # Link ticket to customer
            cursor.execute("""
                INSERT INTO Purchased_By (Ticket_ID, Customer_email) 
                VALUES (%s, %s)
            """, (ticket_id, session['email']))

            conn.commit()

        #flash(f'Payment successful! Your Ticket ID is {ticket_id}.', 'success')
        return redirect(url_for('customer_home'))

    except Exception as e:
        print("Error during purchase:", e)
        flash("An error occurred during payment. Please try again.", "danger")
        return redirect(url_for('customer_home'))

# Displays past flights of a logged-in customer
@app.route('/previous_flights')
def previous_flights():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash('Please log in to view your previous flights.', 'danger')
        return redirect(url_for('login'))

    customer_email = session['email']

    try:
        with conn.cursor() as cursor:
            query = """
                SELECT 
                    f.Flight_number AS flight_number,
                    f.Departure_date_time AS departure_date_time,
                    f.Arrival_date_time AS arrival_date_time,
                    f.Airline_name AS airline_name,
                    f.Airplane_airline_name AS airplane_airline_name,
                    f.Identification_number AS identification_number,
                    f.Departure_airport_code AS departure_airport_code,
                    f.Arrival_airport_code AS arrival_airport_code
                FROM Ticket t
                JOIN Purchased_By pb ON t.Ticket_ID = pb.Ticket_ID
                JOIN Flight f ON t.Flight_number = f.Flight_number 
                             AND t.Departure_date_time = f.Departure_date_time
                             AND t.Airline_name = f.Airline_name
                WHERE pb.Customer_email = %s
                  AND f.Arrival_date_time < NOW()
                ORDER BY f.Arrival_date_time DESC
            """
            cursor.execute(query, (customer_email,))
            previous_flights = cursor.fetchall()

        return render_template('previous_flights.html', previous_flights=previous_flights)

    except Exception as e:
        print("Error fetching previous flights:", e)
        flash("An error occurred while retrieving your previous flights.", "danger")
        return redirect(url_for('customer_home'))

# Loads rating/comment form for a completed flight
@app.route('/rate_comment', methods=['GET'])
def rate_comment():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash('Please log in to rate flights.', 'danger')
        return redirect(url_for('login'))

    flight_number = request.args.get('flight_number')
    departure_date_time = request.args.get('departure_date_time')

    if not flight_number or not departure_date_time:
        flash("Invalid flight selection.", "danger")
        return redirect(url_for('previous_flights'))

    try:
        with conn.cursor() as cursor:
            # Fetch flight details including airline name
            cursor.execute("""
                SELECT Flight_number, Departure_date_time, Airline_name
                FROM Flight
                WHERE Flight_number = %s AND Departure_date_time = %s
            """, (flight_number, departure_date_time))
            
            flight = cursor.fetchone()

            if not flight:
                flash("Flight not found.", "danger")
                return redirect(url_for('previous_flights'))

        return render_template('rate_comment.html', flight=flight)

    except Exception as e:
        print("Error loading rate/comment page:", e)
        flash("An error occurred. Please try again.", "danger")
        return redirect(url_for('previous_flights'))

# Submits a flight review (if not already reviewed)
@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash('Please log in to submit a review.', 'danger')
        return redirect(url_for('login'))

    flight_number = request.form['flight_number']
    departure_date_time = request.form['departure_date_time']
    airline_name = request.form['airline_name']
    rate = int(request.form['rating'])
    comment = request.form['comment']
    customer_email = session['email']

    try:
        with conn.cursor() as cursor:
            # Check if review already exists
            cursor.execute("""
                SELECT * FROM Review
                WHERE Flight_number = %s AND Departure_date_time = %s 
                      AND Airline_name = %s AND Customer_email = %s
            """, (flight_number, departure_date_time, airline_name, customer_email))

            if cursor.fetchone():
                flash("You have already reviewed this flight.", "info")
                return redirect(url_for('customer_home'))

            # Insert review
            cursor.execute("""
                INSERT INTO Review (Flight_number, Departure_date_time, Airline_name, Customer_email, Rate, Comment)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (flight_number, departure_date_time, airline_name, customer_email, rate, comment))

            conn.commit()

        #flash("Thank you! Your review has been submitted.", "success")
        return redirect(url_for('previous_flights'))

    except Exception as e:
        print("Error submitting review:", e)
        flash("An error occurred while submitting your review.", "danger")
        return redirect(url_for('previous_flights'))

# Staff routes
# Handles staff registration and inserts contact info
@app.route('/register_staff', methods=['POST'])
def register_staff():
    try:
        username = request.form['username']
        airline_name = request.form['airline_name']
        password = hash_password(request.form['password'])  # Hash here
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        staff_emails = request.form.getlist('staff_emails[]')
        staff_phones = request.form.getlist('staff_phones[]')

        with conn.cursor() as cursor:
            # Check if airline exists
            cursor.execute("SELECT * FROM Airline WHERE Name = %s", (airline_name,))
            existing_airline = cursor.fetchone()
            if not existing_airline:
                flash("The airline name provided does not exist in the system.", "danger")
                return redirect(url_for('register'))
            
            # Check for username conflict
            cursor.execute("SELECT * FROM Airline_Staff WHERE Username = %s", (username,))
            if cursor.fetchone():
                flash("Username is already registered.", "warning")
                return redirect(url_for('home'))

            # Insert staff
            cursor.execute("""
                INSERT INTO Airline_Staff (Username, Airline_name, Password, First_name, Last_name, Date_of_birth)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, airline_name, password, first_name, last_name, date_of_birth))

            # Insert emails
            for email in staff_emails:
                cursor.execute("INSERT INTO Emails (Airline_staff_username, Staff_email) VALUES (%s, %s)", (username, email))

            # Insert phones
            for phone in staff_phones:
                cursor.execute("INSERT INTO Phone_Numbers (Airline_staff_username, Staff_phone_number) VALUES (%s, %s)", (username, phone))

            conn.commit()

        flash("Staff registration successful. Please log in.", "success")
        return redirect(url_for('login'))

    except Exception as e:
        print("Staff registration error:", e)
        flash("An error occurred during staff registration.", "danger")
        return redirect(url_for('register'))

# Handles staff login
@app.route('/staff_login', methods=['POST'])
def staff_login():
    
    try:
        
        username = request.form['staff_username']
        password = request.form['staff_password']
        hashed_password = hash_password(password)
        
        print("Login attempt for:", username)  # Now this is safe

        with conn.cursor() as cursor:
            query = "SELECT * FROM Airline_staff WHERE Username = %s AND Password = %s"
            cursor.execute(query, (username,hashed_password))
            staff = cursor.fetchone()
            
            if staff:
                # Start session
                session['user_type'] = 'staff'
                session['username'] = staff['Username']
                session['staff_name'] = staff['First_name']
                #flash('Login successful!', 'success')
                return redirect(url_for('staff_home'))
            else:
                flash('Invalid username or password. Please try again.', 'danger')
                return redirect(url_for('home'))
    
    except Exception as e:
        print("Error during login:", e)
        flash('An error occurred during login. Please try again later.', 'danger')
        return redirect(url_for('login'))

# Staff dashboard
@app.route('/staff_home')
def staff_home():
    if 'user_type' in session and session['user_type'] == 'staff':
        return render_template('staff_home.html', staff_name=session.get('staff_name'))
    else:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

# Staff can view and filter their airline’s flights
@app.route('/view_flights', methods=['GET'])
def view_flights():
    if 'user_type' not in session or session['user_type'] != 'staff':
        flash('Please log in as staff to access this page.', 'danger')
        return redirect(url_for('login'))

    username = session['username']

    try:
        with conn.cursor() as cursor:
            # Get the airline that the staff works for
            cursor.execute("SELECT Airline_name FROM Airline_Staff WHERE Username = %s", (username,))
            airline_info = cursor.fetchone()

            if not airline_info:
                flash("Could not find your airline info.", "danger")
                return redirect(url_for('staff_home'))

            staff_airline = airline_info['Airline_name']

            # Get form filters (or defaults)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            source = request.args.get('source')
            destination = request.args.get('destination')

            today = datetime.now().date()

            if not start_date:
                start_date = today
            else:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

            if not end_date:
                end_date = today + timedelta(days=30)
            else:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            # Build base query
            query = """
                SELECT
                    f.Flight_number,
                    f.Departure_airport_code AS Source,
                    f.Arrival_airport_code AS Destination,
                    f.Departure_date_time AS Departure_time,
                    f.Arrival_date_time AS Arrival_time,
                    f.Flight_status AS Status,
                    (
                       SELECT ROUND(AVG(Rate), 2)
                       FROM Review r
                       WHERE r.Flight_number = f.Flight_number
                       AND r.Departure_date_time = f.Departure_date_time
                       AND r.Airline_name = f.Airline_name
                   ) AS avg_rating

                FROM Flight f
                WHERE f.Airline_name = %s
                  AND DATE(f.Departure_date_time) BETWEEN %s AND %s
            """

            params = [staff_airline, start_date, end_date]

            if source:
                query += " AND f.Departure_airport_code = %s"
                params.append(source)
            if destination:
                query += " AND f.Arrival_airport_code = %s"
                params.append(destination)

            query += " ORDER BY f.Departure_date_time ASC"

            cursor.execute(query, tuple(params))
            flights = cursor.fetchall()

            # Get list of airport codes for dropdown
            cursor.execute("SELECT DISTINCT Code FROM Airport")
            airports = [row['Code'] for row in cursor.fetchall()]

            return render_template('view_flights.html', flights=flights, airports=airports, start_date=start_date, end_date=end_date)

    except Exception as e:
        print("Error in view_flights:", e)
        flash("An error occurred loading flights.", "danger")
        return redirect(url_for('staff_home'))

# Allows staff to see the list of customers booked on a specific flight
@app.route('/view_customers', methods=['GET'])
def view_customers():
    if 'user_type' not in session or session['user_type'] != 'staff':
        flash('Please log in as staff to access this page.', 'danger')
        return redirect(url_for('login'))

    flight_number = request.args.get('Flight_number')

    try:
        with conn.cursor() as cursor:
            query = """SELECT DISTINCT
                    c.Name AS name,
                    c.Email AS email
                FROM Ticket t
                JOIN Purchased_by purch ON t.Ticket_ID = purch.Ticket_ID 
                JOIN Customer c ON purch.Customer_Email = c.Email
                WHERE t.Flight_number = %s
            """
            cursor.execute(query, (flight_number,))
            customers = cursor.fetchall()

            return render_template('flight_customer_list.html', customers=customers, flight_number=flight_number)

    except Exception as e:
        print("Error fetching customers:", e)
        flash('Error loading customers.', 'danger')
        return redirect(url_for('view_flights'))

# Allows staff to update the flight status (e.g. Delayed)
@app.route('/update_status', methods=['POST'])
def update_status():
    if 'user_type' not in session or session['user_type'] != 'staff':
        flash('Please log in as staff to access this page.', 'danger')
        return redirect(url_for('login'))

    flight_number = request.form.get('Flight_number')
    new_status = request.form.get('new_status')

    try:
        with conn.cursor() as cursor:
            # First: Check if the flight is in the future or today
            query_check = """
                SELECT Departure_date_time
                FROM Flight
                WHERE Flight_number = %s
            """
            cursor.execute(query_check, (flight_number,))
            flight = cursor.fetchone()

            if not flight:
                flash('Flight not found.', 'danger')
                return redirect(url_for('view_flights'))

            departure_time = flight['Departure_date_time']
            now = datetime.now()

            # Compare departure date/time
            if departure_time.date() >= now.date():
                # If flight is today or future ➔ Allow status update
                query_update = """
                    UPDATE Flight
                    SET Flight_status = %s
                    WHERE Flight_number = %s
                """
                cursor.execute(query_update, (new_status, flight_number))
                conn.commit()
                #flash('Flight status updated successfully.', 'success')
            else:
                flash('Cannot update status of past flights.', 'danger')

            return redirect(url_for('view_flights'))

    except Exception as e:
        print("Error updating flight status:", e)
        flash('Error occurred while updating flight status.', 'danger')
        return redirect(url_for('view_flights'))

# Displays flight reviews submitted by customers
@app.route('/view_ratings', methods=['GET'])
def view_ratings():
    if 'user_type' not in session or session['user_type'] != 'staff':
        flash('Please log in as staff to access this page.', 'danger')
        return redirect(url_for('login'))

    flight_number = request.args.get('Flight_number')

    try:
        with conn.cursor() as cursor:
            query_flight = """SELECT Flight_number,
                        Airline_name,
                        Departure_date_time
                FROM Flight
                WHERE Flight_number = %s
            """
            cursor.execute(query_flight, (flight_number,))
            flight = cursor.fetchone()

            if not flight:
                flash('Flight not found.', 'danger')
                return redirect(url_for('view_flights'))


        with conn.cursor() as cursor:
            query_reviews = """SELECT Customer_email AS email,
                        Rate AS rating,
                        Comment as comment
                FROM Review
                WHERE Flight_number = %s
            """
            cursor.execute(query_reviews, (flight_number,))
            reviews = cursor.fetchall()

        if reviews:
            avg_rating = sum([r['rating'] for r in reviews]) / len(reviews)
        else:
            avg_rating = None

        return render_template('view_ratings.html', reviews=reviews, flight=flight, avg_rating=avg_rating)

    except Exception as e:
        print("Error fetching reviews:", e)
        flash('Error loading reviews.', 'danger')
        return redirect(url_for('view_flights'))

# Allows staff to create new flights for their airline
@app.route('/create_flight', methods=['GET', 'POST'])
def create_flight():
    if 'user_type' not in session or session['user_type'] != 'staff':
        flash('Please log in as staff to access this page.', 'danger')
        return redirect(url_for('login'))

    username = session['username']

    try:
        with conn.cursor() as cursor:
            # Get the airline the staff works for
            cursor.execute("SELECT Airline_name FROM Airline_Staff WHERE Username = %s", (username,))
            airline_info = cursor.fetchone()

            if not airline_info:
                flash("Could not find your airline info.", "danger")
                return redirect(url_for('staff_home'))

            staff_airline = airline_info['Airline_name']

            # ------------------ POST: Add new flight ------------------
            if request.method == 'POST':
                flight_number = request.form['flight_number']
                departure_airport = request.form['departure_airport']
                arrival_airport = request.form['arrival_airport']
                departure_time = request.form['departure_time']
                arrival_time = request.form['arrival_time']
                airline_name = request.form['airline_name']
                identification_number = request.form['identification_number']
                airplane_airline = request.form['airplane_airline']
                base_price = request.form['base_price']
                status = request.form['status']

                # Safety check: prevent staff from inserting flights under another airline
                if airline_name != staff_airline:
                    flash("You can only create flights for your own airline.", "danger")
                    return redirect(url_for('create_flight'))

                # Check airplane exists
                cursor.execute("""
                    SELECT 1 FROM Airplane 
                    WHERE Identification_number = %s AND Airline_name = %s
                """, (identification_number, airplane_airline))
                if not cursor.fetchone():
                    flash("Specified airplane not found in your airline.", "danger")
                    return redirect(url_for('create_flight'))

                # Check departure airport exists
                cursor.execute("SELECT 1 FROM Airport WHERE Code = %s", (departure_airport,))
                if not cursor.fetchone():
                    flash("Departure airport does not exist.", "danger")
                    return redirect(url_for('create_flight'))

                # Check arrival airport exists
                cursor.execute("SELECT 1 FROM Airport WHERE Code = %s", (arrival_airport,))
                if not cursor.fetchone():
                    flash("Arrival airport does not exist.", "danger")
                    return redirect(url_for('create_flight'))

                # Optional: Check if flight already exists
                cursor.execute("""
                        SELECT * FROM Flight
                        WHERE Flight_number = %s AND Airline_name = %s AND Departure_date_time = %s
                """, (flight_number, airline_name, departure_time))
                existing = cursor.fetchone()
                if existing:
                    flash("Flight with that number and departure time already exists.", "danger")
                    return redirect(url_for('create_flight'))

                # Insert new flight
                insert_query = """
                    INSERT INTO Flight (
                        Flight_number, Departure_airport_code, Arrival_airport_code,
                        Departure_date_time, Arrival_date_time, Airline_name,
                        Identification_number, Airplane_airline_name, Base_price, Flight_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (
                    flight_number, departure_airport, arrival_airport,
                    departure_time, arrival_time, airline_name,
                    identification_number, airplane_airline, base_price, status
                ))
                conn.commit()
                #flash("Flight created successfully!", "success")

            # ------------------ GET: Display upcoming flights ------------------
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=30)

            cursor.execute("""
                SELECT 
                    Flight_number AS flight_number,
                    Departure_airport_code AS departure_airport,
                    Arrival_airport_code AS arrival_airport,
                    Departure_date_time AS departure_time,
                    Arrival_date_time AS arrival_time,
                    Flight_status AS status
                FROM Flight
                WHERE Airline_name = %s AND DATE(Departure_date_time) BETWEEN %s AND %s
                ORDER BY Departure_date_time ASC
            """, (staff_airline, start_date, end_date))
            future_flights = cursor.fetchall()

            return render_template('create_flight.html',
                                   future_flights=future_flights,
                                   staff_airline=staff_airline,
                                   start_date=start_date,
                                   end_date=end_date)

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash("An error occurred while creating the flight.", "danger")
        return redirect(url_for('staff_home'))

# Allows staff to register new airplanes into the system
@app.route('/add_airplane', methods=['GET', 'POST'])
def add_airplane():
    if 'user_type' not in session or session['user_type'] != 'staff':
        flash('Please log in as staff to access this page.', 'danger')
        return redirect(url_for('login'))

    username = session['username']

    try:
        with conn.cursor() as cursor:
            # Find the airline the staff works for
            cursor.execute("SELECT Airline_name FROM Airline_staff WHERE Username = %s", (username,))
            staff_info = cursor.fetchone()

            if not staff_info:
                flash('Could not find your airline info.', 'danger')
                return redirect(url_for('staff_home'))

            staff_airline = staff_info['Airline_name']

            if request.method == 'POST':
                # Staff is submitting a new airplane
                identification_number = request.form['identification_number']
                airplane_airline = request.form['airplane_airline']
                number_of_seats = request.form['number_of_seats']
                manufacturing_company = request.form['manufacturing_company']

                # Confirm that the entered airline matches the staff's airline
                if airplane_airline != staff_airline:
                    flash('You can only add airplanes for your own airline.', 'danger')
                    return redirect(url_for('add_airplane'))

                cursor.execute("SELECT * FROM Airline WHERE Name = %s", (airplane_airline,))
                existing_airline = cursor.fetchone()
                if not existing_airline:
                    flash('The airline name provided does not exist in the Airline table.', 'danger')
                    return redirect(url_for('add_airplane'))

                check_query = """
                    SELECT *
                    FROM Airplane
                    WHERE Identification_number = %s AND Airline_name = %s
                """
                cursor.execute(check_query, (identification_number, airplane_airline))
                existing_airplane = cursor.fetchone()

                if existing_airplane:
                    flash('An airplane with that Identification Number and Airline already exists.', 'danger')
                    return redirect(url_for('add_airplane'))
                
                # Insert the new airplane
                insert_query = """
                    INSERT INTO Airplane (Identification_number, Airline_name, Number_of_seats, Manufacturing_company)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (identification_number, airplane_airline, number_of_seats, manufacturing_company))
                conn.commit()

                #flash('Airplane added successfully!', 'success')

            # After insertion (or just opening the page), show all airplanes for staff's airline
            fetch_query = """
                SELECT Identification_number, Airline_name, Number_of_seats, Manufacturing_company
                FROM Airplane
                WHERE Airline_name = %s
            """
            cursor.execute(fetch_query, (staff_airline,))
            airplanes = cursor.fetchall()


            fetch_query = """
                SELECT Identification_number, Airline_name, Number_of_seats, Manufacturing_company
                FROM Airplane
                WHERE Airline_name = %s
            """
            cursor.execute(fetch_query, (staff_airline,))
            airplanes = cursor.fetchall()
            conn.commit()
            return render_template('add_airplane.html', airplanes=airplanes)

    except Exception as e:
        print("Error in add_airplane:", e)
        flash('An error occurred while adding airplane.', 'danger')
        return redirect(url_for('staff_home'))

# Allows staff to add new airports to the system
@app.route('/add_airport', methods=['GET', 'POST'])
def add_airport():
    if 'user_type' not in session or session['user_type'] != 'staff':
        flash('Please log in as staff to access this page.', 'danger')
        return redirect(url_for('login'))

    username = session['username']

    try:
        with conn.cursor() as cursor:
            if request.method == 'POST':
                # Staff is submitting a new airport
                airport_code = request.form['airport_code']
                airport_name = request.form['airport_name']
                city = request.form['city']
                country = request.form['country']


                check_query = """
                    SELECT *
                    FROM Airport
                    WHERE Code = %s
                """
                cursor.execute(check_query, (airport_code))
                existing_airport = cursor.fetchone()

                if existing_airport:
                    flash('An airport with that code already exists.', 'danger')
                    return redirect(url_for('add_airport'))
                
                # Insert the new airplane
                insert_query = """
                    INSERT INTO Airport (Code, Name, City, Country)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (airport_code, airport_name, city, country))
                conn.commit()

                #flash('Airport added successfully!', 'success')

            # Always fetch the list of airports to display after adding or just opening the page
            fetch_query = """
                SELECT Code, Name, City, Country
                FROM Airport
            """
            cursor.execute(fetch_query)
            airports = cursor.fetchall()
            conn.commit()
            return render_template('add_airport.html', airports=airports)

    except Exception as e:
        print("Error in add_airport:", e)
        flash('An error occurred while adding airport.', 'danger')
        return redirect(url_for('staff_home'))

# Generates a monthly sales report using ticket purchases
@app.route('/view_reports', methods=['GET'])
def view_reports():
   if 'user_type' not in session or session['user_type'] != 'staff':
       flash('Please log in as staff to access this page.', 'danger')
       return redirect(url_for('login'))


   try:
       with conn.cursor() as cursor:
           # Get date range from query parameters
           start_str = request.args.get('start_date')
           end_str = request.args.get('end_date')


           today = datetime.today()


           # Default range: last year to today
           if not start_str or not end_str:
               end_date = today
               start_date = end_date.replace(year=end_date.year - 1)
           else:
               start_date = datetime.strptime(start_str, '%Y-%m-%d')
               end_date = datetime.strptime(end_str, '%Y-%m-%d')


           # Fetch number of tickets sold per month
           query = """
               SELECT
                   DATE_FORMAT(Purchase_date_time, '%%Y-%%m') AS month,
                   COUNT(*) AS tickets_sold
               FROM Ticket
               WHERE Purchase_date_time BETWEEN %s AND %s
               GROUP BY month
               ORDER BY month
           """
           cursor.execute(query, (start_date, end_date))
           results = cursor.fetchall()


           labels = [row['month'] for row in results]
           counts = [row['tickets_sold'] for row in results]


           return render_template(
               'view_reports.html',
               monthly_sales=results,
               monthly_sales_labels=labels,
               monthly_sales_data=counts,
               start_date=start_date.strftime('%Y-%m'),
               end_date=end_date.strftime('%Y-%m')
           )


   except Exception as e:
       print("Error generating report:", e)
       flash("An error occurred while generating the report.", "danger")
       return redirect(url_for('staff_home'))

if __name__ == '__main__':
    app.run(debug=True)
