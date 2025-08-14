CREATE TABLE Airline (
    Name VARCHAR(50) PRIMARY KEY
);

CREATE TABLE Airplane (
    Identification_number VARCHAR(20),
    Airline_name VARCHAR(50),
    Number_of_seats INT CHECK (Number_of_seats > 0),
    Manufacturing_company VARCHAR(100),
    
    PRIMARY KEY (Identification_number, Airline_name),
    FOREIGN KEY (Airline_name) REFERENCES Airline(Name)
);

CREATE TABLE Airport (
    Code CHAR(3) PRIMARY KEY,
    Name VARCHAR(60),
    City VARCHAR(50),
    Country VARCHAR(50)
);

CREATE TABLE Flight (
    Flight_number VARCHAR(10),
    Departure_date_time DATETIME,
    Airline_name VARCHAR(50),
    Airplane_airline_name VARCHAR(50),
    Identification_number VARCHAR(20),
    Departure_airport_code CHAR(3),
    Arrival_airport_code CHAR(3),
    Arrival_date_time DATETIME,
    Base_price DECIMAL(10,2),
    Flight_status VARCHAR(50),

    PRIMARY KEY (Flight_number, Departure_date_time, Airline_name),
    FOREIGN KEY (Airline_name) REFERENCES Airline(Name),
    FOREIGN KEY (Identification_number, Airplane_airline_name) REFERENCES Airplane(Identification_number, Airline_name),
    FOREIGN KEY (Departure_airport_code) REFERENCES Airport(Code),
    FOREIGN KEY (Arrival_airport_code) REFERENCES Airport(Code)
);

CREATE TABLE Customer (
    Email VARCHAR(30) PRIMARY KEY,
    Name VARCHAR(75),
    Password VARCHAR(50),
    Building_number INT,
    Street VARCHAR(100),
    City VARCHAR(100),
    State VARCHAR(100),
    Phone_number VARCHAR(20),
    Passport_number VARCHAR(50) UNIQUE,
    Passport_expiration DATE,
    Passport_country VARCHAR(50),
    Date_of_birth DATE
);

CREATE TABLE Ticket (
    Ticket_ID VARCHAR(50) PRIMARY KEY,
    Flight_number VARCHAR(10),
    Departure_date_time DATETIME,
    Airline_name VARCHAR(50),
    Sold_price DECIMAL(10,2),
    Card_type VARCHAR(50),
    Card_number VARCHAR(30),
    Name_on_card VARCHAR(100),
    Expiration_date DATE,
    Purchase_date_time DATETIME,

    FOREIGN KEY (Flight_number, Departure_date_time, Airline_name) REFERENCES Flight(Flight_number, Departure_date_time, Airline_name)
);

CREATE TABLE Purchased_By (
    Ticket_ID VARCHAR(50) PRIMARY KEY,
    Customer_email VARCHAR(30),

    FOREIGN KEY (Ticket_ID) REFERENCES Ticket(Ticket_ID),
    FOREIGN KEY (Customer_email) REFERENCES Customer(Email)
);

CREATE TABLE Review (
    Flight_number VARCHAR(50),
    Departure_date_time DATETIME,
    Airline_name VARCHAR(100),
    Customer_email VARCHAR(30),
    Rate INT CHECK (Rate BETWEEN 1 AND 5),
    Comment VARCHAR(250),

    PRIMARY KEY (Flight_number, Departure_date_time, Airline_name, Customer_email),
    FOREIGN KEY (Flight_number, Departure_date_time, Airline_name) REFERENCES Flight(Flight_number, Departure_date_time, Airline_name),
    FOREIGN KEY (Customer_email) REFERENCES Customer(Email)
);

CREATE TABLE Airline_Staff (
    Username VARCHAR(50) PRIMARY KEY,
    Airline_name VARCHAR(100),
    Password VARCHAR(50),
    First_name VARCHAR(50),
    Last_name VARCHAR(50),
    Date_of_birth DATE,

    FOREIGN KEY (Airline_name) REFERENCES Airline(Name)
);

CREATE TABLE Phone_Numbers (
    Airline_staff_username VARCHAR(50),
    Staff_phone_number VARCHAR(20),
    
    PRIMARY KEY (Airline_staff_username, Staff_phone_number),
    FOREIGN KEY (Airline_staff_username) REFERENCES Airline_Staff(Username)
);

CREATE TABLE Emails (
    Airline_staff_username VARCHAR(50),
    Staff_email VARCHAR(30),
    
    PRIMARY KEY (Airline_staff_username, Staff_email),
    FOREIGN KEY (Airline_staff_username) REFERENCES Airline_Staff(Username)
);
