
INSERT INTO Airline (Name) VALUES ('Jet Blue');

INSERT INTO Airport(Code, Name, City, Country) VALUES ('JFK', 'John F. Kennedy International Airport', 'New York City', 'USA');

INSERT INTO Airport(Code, Name, City, Country) VALUES ('PVG', 'Shanghai Pudong International Airport', 'Shanghai', 'China');

INSERT INTO Customer(Email, Name, Password, Building_number, Street, City, State, Phone_number, Passport_number, Passport_expiration, Passport_country, Date_of_birth) VALUES 
('billybob@gmail.com', 'Billy Bob', 'ILoveBilly', 201, 'Fairfax St', 'New York', 'New York', '646 904 1132', '763478683', '2030-10-02', 'USA', '1970-02-17'), 
('kellyclark@gmail.com', 'Kelly Clark', '18091970', 12, 'Lafayette St', 'New York', 'New York', '6456991123', '678249820', '2028-08-28', 'USA', '1980-02-11'), 
('jim.fall@hotmail.com', 'Jimmy Fall', 'IHateKellyClark123', 3, 'Pine St', 'Seattle', 'Washington', '206 498 5014', '876544352', '2032-04-27', 'USA', '1974-09-19'),
('santa.claus@yahoo.com', 'Santa Claus', 'MerryChristmas', 123, 'Elf Road', 'North Pole', 'North Pole', '605 313 0691', '111114352', '2027-12-27', 'Finland', '1950-03-15');

INSERT INTO Airplane (Identification_number, Airline_name, Number_of_seats, Manufacturing_company) VALUES 
('JB001', 'Jet Blue', 250, 'Airbus'), 
('JB002', 'Jet Blue', 150, 'Boeing'), 
('JB003', 'Jet Blue', 200, 'Embraer');

INSERT INTO Airline_Staff(Username, Airline_name, Password, First_name, Last_name, Date_of_birth) VALUES 
('cm3418', 'Jet Blue', 'vsjhgvss1234', 'Camilla', 'Menendez', '1972-04-28'), 
('ha7378', 'Jet Blue', 'staff_mahmoud74', 'Hamoudi', 'AbuAntar', '1967-12-31');

INSERT INTO Phone_Numbers (Airline_staff_username, Staff_phone_number) VALUES ('cm3418', '800-555-1234');

INSERT INTO Emails (Airline_staff_username, Staff_email) VALUES ('cm3418', 'camilla.menendez@jetblue.com');

INSERT INTO Emails (Airline_staff_username, Staff_email) VALUES ('ha7378', 'hamoudi.abuantar@jetblue.com');

INSERT INTO Phone_Numbers (Airline_staff_username, Staff_phone_number) VALUES ('ha7378', '800-723-4321');

INSERT INTO Flight(Flight_number, Departure_date_time, Airline_name, Airplane_airline_name, Identification_number, Departure_airport_code, Arrival_airport_code, Arrival_date_time, Base_price, Flight_status) VALUES 
('JB100', '2025-04-01 08:00:00', 'Jet Blue', 'Jet Blue', 'JB001', 'JFK', 'PVG', '2025-04-02 09:00:00', 500.00, 'On Time'),
('JB101', '2025-05-04 14:30:00', 'Jet Blue', 'Jet Blue', 'JB002', 'PVG', 'JFK', '2025-05-03 13:45:00', 520.00, 'Delayed');

INSERT INTO Ticket (Ticket_ID, Flight_number, Departure_date_time, Airline_name, Sold_price, Card_type, Card_number, Name_on_card, Expiration_date, Purchase_date_time) VALUES 
('TKT001', 'JB100', '2025-04-01 08:00:00', 'Jet Blue', 500.00, 'Visa', '1234567812345678', 'Billy Bob', '2028-06-30', '2025-04-02 10:00:00'),
('TKT002', 'JB100', '2025-04-01 08:00:00', 'Jet Blue', 500.00, 'MasterCard', '9876543298765432', 'Kelly Clark', '2027-12-31', '2025-04-02 10:30:00'),
('TKT003', 'JB101', '2025-05-04 14:30:00', 'Jet Blue', 520.00, 'Amex', '4567123445671234', 'Jimmy Fall', '2029-04-15', '2025-04-03 09:45:00');

INSERT INTO Purchased_By (Ticket_ID, Customer_email) VALUES 
('TKT001', 'billybob@gmail.com'),
('TKT002', 'kellyclark@gmail.com'),
('TKT003', 'jim.fall@hotmail.com');

