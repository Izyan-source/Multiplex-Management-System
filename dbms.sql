

CREATE DATABASE MultiplexDB;

USE MultiplexDB;

CREATE TABLE Multiplex (
    Multiplex_ID VARCHAR(10) PRIMARY KEY,
    Multiplex_Name VARCHAR(100),
    City VARCHAR(50),
    Address VARCHAR(200),
    Contact_No VARCHAR(15)
);

CREATE TABLE Screen (
    Screen_ID VARCHAR(10) PRIMARY KEY,
    Multiplex_ID VARCHAR(10),
    Screen_Name VARCHAR(20),
    Capacity INT,
    Screen_Type VARCHAR(20),
    FOREIGN KEY (Multiplex_ID) REFERENCES Multiplex(Multiplex_ID)
);

CREATE TABLE Movie (
    Movie_ID VARCHAR(10) PRIMARY KEY,
    Movie_Name VARCHAR(100),
    Genre VARCHAR(50),
    Language VARCHAR(30),
    Duration_Min INT,
    Rating DECIMAL(2,1)
);

CREATE TABLE `Show` (
    Show_ID VARCHAR(10) PRIMARY KEY,
    Movie_ID VARCHAR(10),
    Screen_ID VARCHAR(10),
    Show_Date DATE,
    Show_Time TIME,
    Ticket_Price DECIMAL(8,2),
    FOREIGN KEY (Movie_ID) REFERENCES Movie(Movie_ID),
    FOREIGN KEY (Screen_ID) REFERENCES Screen(Screen_ID)
);

CREATE TABLE Customer (
    Customer_ID VARCHAR(10) PRIMARY KEY,
    Customer_Name VARCHAR(100),
    Phone VARCHAR(15),
    Email VARCHAR(100),
    Gender VARCHAR(10)
);

CREATE TABLE Seat (
    Seat_ID VARCHAR(10) PRIMARY KEY,
    Screen_ID VARCHAR(10),
    Seat_Number VARCHAR(10),
    Seat_Type VARCHAR(20),
    Seat_Status VARCHAR(20),
    FOREIGN KEY (Screen_ID) REFERENCES Screen(Screen_ID)
);

CREATE TABLE Payment (
    Payment_ID VARCHAR(10) PRIMARY KEY,
    Amount DECIMAL(8,2),
    Payment_Mode VARCHAR(20),
    Payment_Date DATE,
    Payment_Status VARCHAR(20)
);

CREATE TABLE Booking (
    Booking_ID VARCHAR(10) PRIMARY KEY,
    Customer_ID VARCHAR(10),
    Show_ID VARCHAR(10),
    Seat_ID VARCHAR(10),
    Payment_ID VARCHAR(10),
    Booking_Date DATE,
    Booking_Time TIME,
    Total_Amount DECIMAL(8,2),
    Booking_Status VARCHAR(20),
    FOREIGN KEY (Customer_ID) REFERENCES Customer(Customer_ID),
    FOREIGN KEY (Show_ID) REFERENCES `Show`(Show_ID),
    FOREIGN KEY (Seat_ID) REFERENCES Seat(Seat_ID),
    FOREIGN KEY (Payment_ID) REFERENCES Payment(Payment_ID)
);

CREATE TABLE Employee (
    Employee_ID VARCHAR(10) PRIMARY KEY,
    Multiplex_ID VARCHAR(10),
    Employee_Name VARCHAR(100),
    Designation VARCHAR(50),
    Phone VARCHAR(15),
    FOREIGN KEY (Multiplex_ID) REFERENCES Multiplex(Multiplex_ID)
);

CREATE TABLE Food_Order (
    Order_ID VARCHAR(10) PRIMARY KEY,
    Booking_ID VARCHAR(10),
    Item_Name VARCHAR(100),
    Quantity INT,
    Total_Price DECIMAL(8,2),
    FOREIGN KEY (Booking_ID) REFERENCES Booking(Booking_ID)
);

INSERT INTO Multiplex
(Multiplex_ID, Multiplex_Name, City, Address, Contact_No)
VALUES
('K7P4X', 'PVR Phoenix Marketcity', 'Pune', 'Viman Nagar', '02066890001'),
('R3M8Q', 'INOX Amanora', 'Pune', 'Hadapsar', '02066890002'),
('T9L2W', 'Cinepolis Seasons Mall', 'Pune', 'Magarpatta', '02066890003'),
('H5V7N', 'City Pride Kothrud', 'Pune', 'Kothrud', '02066890004'),
('C2X6B', 'PVR Pavilion Mall', 'Pune', 'SB Road', '02066890005');

INSERT INTO Screen
(Screen_ID, Multiplex_ID, Screen_Name, Capacity, Screen_Type)
VALUES
('S8Q2M', 'K7P4X', 'Screen 1', 220, 'IMAX'),
('S4L9R', 'R3M8Q', 'Screen 2', 180, '3D'),
('S7N3K', 'T9L2W', 'Screen 1', 200, '2D'),
('S5X8P', 'H5V7N', 'Screen 3', 150, '2D'),
('S2W6D', 'C2X6B', 'Screen 2', 250, '3D');

INSERT INTO Movie
(Movie_ID, Movie_Name, Genre, Language, Duration_Min, Rating)
VALUES
('M6Q2T', 'Avengers: Endgame', 'Action', 'English', 181, 8.4),
('M9X4P', 'Pushpa 2', 'Action', 'Telugu', 201, 7.9),
('M3K7L', 'Chhaava', 'Historical', 'Hindi', 165, 8.2),
('M8R5V', 'Interstellar', 'Sci-Fi', 'English', 169, 8.7),
('M2N6B', 'Sitaare Zameen Par', 'Drama', 'Hindi', 155, 8.0),
('M5T8Q', 'Dangal', 'Sports', 'Hindi', 161, 8.6),
('M7P3L', 'Jawan', 'Action', 'Hindi', 169, 7.8),
('M4X9R', 'Inception', 'Sci-Fi', 'English', 148, 8.8);

INSERT INTO `Show`
(Show_ID, Movie_ID, Screen_ID, Show_Date, Show_Time, Ticket_Price)
VALUES
('W7P3K', 'M6Q2T', 'S8Q2M', '2026-08-15', '10:00:00', 450.00),
('Q4L8X', 'M9X4P', 'S4L9R', '2026-08-15', '13:30:00', 300.00),
('R2T6M', 'M3K7L', 'S7N3K', '2026-08-15', '16:00:00', 280.00),
('X9B5N', 'M8R5V', 'S5X8P', '2026-08-15', '18:30:00', 350.00),
('P6V3C', 'M2N6B', 'S2W6D', '2026-08-15', '21:00:00', 320.00),
('L8Q4M', 'M5T8Q', 'S8Q2M', '2026-08-16', '12:00:00', 400.00),
('N3K7P', 'M7P3L', 'S4L9R', '2026-08-16', '15:30:00', 300.00),
('T5R8X', 'M4X9R', 'S7N3K', '2026-08-16', '19:00:00', 380.00);

INSERT INTO Customer
(Customer_ID, Customer_Name, Phone, Email, Gender)
VALUES
('C8K2M', 'Izyan Lalani', '9876543210', 'izyan@gmail.com', 'Male'),
('C4R7P', 'Aarav Sharma', '9823012345', 'aarav@gmail.com', 'Male'),
('C9T3X', 'Riya Mehta', '9765432109', 'riya@gmail.com', 'Female'),
('C5N8Q', 'Sneha Kulkarni', '9898989898', 'sneha@gmail.com', 'Female'),
('C2L6V', 'Aditya Patil', '9123456789', 'aditya@gmail.com', 'Male'),
('C7M4K', 'Rahul Desai', '9812345678', 'rahul@gmail.com', 'Male'),
('C3P8R', 'Ananya Joshi', '9753124680', 'ananya@gmail.com', 'Female'),
('C6X2N', 'Vikram Shah', '9867452310', 'vikram@gmail.com', 'Male'),
('C9Q5T', 'Meera Nair', '9988776655', 'meera@gmail.com', 'Female'),
('C4L7X', 'Kabir Malhotra', '9876123450', 'kabir@gmail.com', 'Male'),
('C8R3M', 'Tanvi Deshpande', '9765123480', 'tanvi@gmail.com', 'Female'),
('C5K9P', 'Arjun Kapoor', '9897123456', 'arjun@gmail.com', 'Male'),
('C2T6V', 'Pooja Agarwal', '9810987654', 'pooja@gmail.com', 'Female'),
('C7N4Q', 'Rohan Mehta', '9922334455', 'rohan@gmail.com', 'Male'),
('C3X8L', 'Kavya Iyer', '9845671230', 'kavya@gmail.com', 'Female');

INSERT INTO Seat
(Seat_ID, Screen_ID, Seat_Number, Seat_Type, Seat_Status)
VALUES
('E7K3P', 'S8Q2M', 'A1', 'Premium', 'Booked'),
('E4X9L', 'S4L9R', 'B5', 'Regular', 'Booked'),
('E8M2R', 'S7N3K', 'C10', 'Regular', 'Booked'),
('E5Q7T', 'S5X8P', 'D7', 'Premium', 'Booked'),
('E3V6N', 'S2W6D', 'E3', 'Recliner', 'Booked'),
('E9P4K', 'S8Q2M', 'A2', 'Premium', 'Booked'),
('E6R8M', 'S8Q2M', 'A3', 'Regular', 'Booked'),
('E2T5X', 'S4L9R', 'B6', 'Regular', 'Booked'),
('E7N3Q', 'S4L9R', 'B7', 'Premium', 'Booked'),
('E5K8R', 'S7N3K', 'C11', 'Regular', 'Booked'),
('E4M9P', 'S7N3K', 'C12', 'Premium', 'Booked'),
('E8Q2L', 'S5X8P', 'D8', 'Regular', 'Booked'),
('E6V3T', 'S2W6D', 'E4', 'Recliner', 'Booked'),
('E9X5N', 'S2W6D', 'E5', 'Regular', 'Booked'),
('E3R7K', 'S8Q2M', 'A4', 'Premium', 'Booked');

INSERT INTO Payment
(Payment_ID, Amount, Payment_Mode, Payment_Date, Payment_Status)
VALUES
('P7M2X', 450.00, 'UPI', '2026-08-12', 'Paid'),
('P4Q8L', 300.00, 'Card', '2026-08-12', 'Paid'),
('P9R3K', 280.00, 'Cash', '2026-08-12', 'Paid'),
('P5T7N', 350.00, 'UPI', '2026-08-12', 'Pending'),
('P2V6B', 320.00, 'Net Banking', '2026-08-12', 'Paid'),
('P8K4M', 450.00, 'Card', '2026-08-12', 'Paid'),
('P3X7Q', 450.00, 'UPI', '2026-08-12', 'Paid'),
('P6N2R', 300.00, 'Card', '2026-08-12', 'Paid'),
('P9L5T', 300.00, 'UPI', '2026-08-12', 'Paid'),
('P4M8X', 280.00, 'Cash', '2026-08-12', 'Paid'),
('P7Q3K', 280.00, 'UPI', '2026-08-12', 'Paid'),
('P2R6N', 350.00, 'Card', '2026-08-12', 'Paid'),
('P5X9L', 320.00, 'UPI', '2026-08-13', 'Paid'),
('P8T4V', 320.00, 'Card', '2026-08-13', 'Paid'),
('P3K7M', 400.00, 'UPI', '2026-08-13', 'Paid');

INSERT INTO Booking
(Booking_ID, Customer_ID, Show_ID, Seat_ID, Payment_ID,
Booking_Date, Booking_Time, Total_Amount, Booking_Status)
VALUES
('B8K3R', 'C8K2M', 'W7P3K', 'E7K3P', 'P7M2X',
'2026-08-12', '09:15:00', 450.00, 'Confirmed'),

('B4X7L', 'C4R7P', 'Q4L8X', 'E4X9L', 'P4Q8L',
'2026-08-12', '10:30:00', 300.00, 'Confirmed'),

('B9M2T', 'C9T3X', 'R2T6M', 'E8M2R', 'P9R3K',
'2026-08-12', '12:45:00', 280.00, 'Confirmed'),

('B5Q8N', 'C5N8Q', 'X9B5N', 'E5Q7T', 'P5T7N',
'2026-08-12', '14:20:00', 350.00, 'Pending'),

('B3V6P', 'C2L6V', 'P6V3C', 'E3V6N', 'P2V6B',
'2026-08-12', '16:10:00', 320.00, 'Confirmed'),

('B7R4M', 'C7M4K', 'W7P3K', 'E9P4K', 'P8K4M',
'2026-08-12', '17:25:00', 450.00, 'Confirmed'),

('B2X8Q', 'C3P8R', 'W7P3K', 'E6R8M', 'P3X7Q',
'2026-08-12', '18:05:00', 450.00, 'Confirmed'),

('B6K3T', 'C6X2N', 'Q4L8X', 'E2T5X', 'P6N2R',
'2026-08-12', '19:15:00', 300.00, 'Confirmed'),

('B9P5L', 'C9Q5T', 'Q4L8X', 'E7N3Q', 'P9L5T',
'2026-08-12', '19:45:00', 300.00, 'Confirmed'),

('B4R8N', 'C4L7X', 'R2T6M', 'E5K8R', 'P4M8X',
'2026-08-12', '20:10:00', 280.00, 'Confirmed'),

('B7T2K', 'C8R3M', 'R2T6M', 'E4M9P', 'P7Q3K',
'2026-08-12', '20:40:00', 280.00, 'Confirmed'),

('B3M6X', 'C5K9P', 'X9B5N', 'E8Q2L', 'P2R6N',
'2026-08-12', '21:10:00', 350.00, 'Confirmed'),

('B8Q4P', 'C2T6V', 'P6V3C', 'E6V3T', 'P5X9L',
'2026-08-13', '09:30:00', 320.00, 'Confirmed'),

('B5L9R', 'C7N4Q', 'P6V3C', 'E9X5N', 'P8T4V',
'2026-08-13', '10:15:00', 320.00, 'Confirmed'),

('B2N7K', 'C3X8L', 'L8Q4M', 'E3R7K', 'P3K7M',
'2026-08-13', '11:20:00', 400.00, 'Confirmed');

INSERT INTO Employee
(Employee_ID, Multiplex_ID, Employee_Name, Designation, Phone)
VALUES
('E9K4M', 'K7P4X', 'Rahul Joshi', 'Manager', '9876500001'),
('E2R7Q', 'R3M8Q', 'Priya Deshmukh', 'Cashier', '9876500002'),
('E6X3L', 'T9L2W', 'Karan Shah', 'Projection Operator', '9876500003'),
('E8N5P', 'H5V7N', 'Neha Patil', 'Security', '9876500004'),
('E4V2T', 'C2X6B', 'Rohit Kulkarni', 'Food Counter', '9876500005');

INSERT INTO Food_Order
(Order_ID, Booking_ID, Item_Name, Quantity, Total_Price)
VALUES
('O7K3X', 'B8K3R', 'Large Popcorn', 1, 350.00),
('O4Q9L', 'B4X7L', 'Coke', 2, 240.00),
('O8M2P', 'B9M2T', 'Nachos', 1, 220.00),
('O5R7N', 'B5Q8N', 'Combo Meal', 1, 499.00),
('O3V6K', 'B3V6P', 'Popcorn + Pepsi Combo', 2, 700.00),
('O9X4M', 'B7R4M', 'Cheese Nachos', 1, 280.00),
('O2K8P', 'B2X8Q', 'Large Popcorn', 1, 350.00),
('O6Q3L', 'B6K3T', 'Coke', 2, 240.00),
('O4N7R', 'B9P5L', 'Veg Sandwich', 1, 180.00),
('O8T2M', 'B4R8N', 'Nachos', 1, 220.00),
('O5P9K', 'B7T2K', 'Popcorn', 1, 200.00),
('O3L6X', 'B3M6X', 'Combo Meal', 1, 499.00),
('O7R4Q', 'B8Q4P', 'Coke', 1, 120.00),
('O2M8N', 'B5L9R', 'Large Popcorn', 1, 350.00),
('O6X3T', 'B2N7K', 'Nachos', 1, 220.00);

SHOW TABLES;

SELECT * FROM Multiplex;

SELECT * FROM Screen;

SELECT * FROM Movie;

SELECT * FROM `Show`;

SELECT * FROM Customer;

SELECT * FROM Seat;

SELECT * FROM Payment;

SELECT * FROM Booking;

SELECT * FROM Employee;

SELECT * FROM Food_Order;


SELECT
    Booking.Booking_ID,
    Customer.Customer_Name,
    Movie.Movie_Name,
    Booking.Booking_Date,
    Booking.Booking_Time,
    Booking.Total_Amount
FROM Booking
JOIN Customer
ON Booking.Customer_ID = Customer.Customer_ID
JOIN `Show`
ON Booking.Show_ID = `Show`.Show_ID
JOIN Movie
ON `Show`.Movie_ID = Movie.Movie_ID;


SELECT
    Movie.Movie_Name,
    COUNT(Booking.Booking_ID) AS Total_Bookings
FROM Movie
JOIN `Show`
ON Movie.Movie_ID = `Show`.Movie_ID
JOIN Booking
ON `Show`.Show_ID = Booking.Show_ID
GROUP BY Movie.Movie_Name;



SELECT Movie_Name, Rating
FROM Movie
WHERE Rating > (
    SELECT AVG(Rating)
    FROM Movie
);



SELECT DISTINCT
    Customer.Customer_ID,
    Customer.Customer_Name
FROM Customer
JOIN Booking
    ON Customer.Customer_ID = Booking.Customer_ID




SELECT
    Movie.Movie_Name,
    SUM(Booking.Total_Amount) AS Total_Revenue
FROM Movie
JOIN `Show`
    ON Movie.Movie_ID = `Show`.Movie_ID
JOIN Booking
    ON `Show`.Show_ID = Booking.Show_ID
WHERE Booking.Booking_Status = 'Confirmed'
GROUP BY Movie.Movie_Name;



SELECT
    Movie.Movie_Name,
    COUNT(Booking.Booking_ID) AS Total_Bookings
FROM Movie
JOIN `Show`
    ON Movie.Movie_ID = `Show`.Movie_ID
JOIN Booking
    ON `Show`.Show_ID = Booking.Show_ID
GROUP BY Movie.Movie_Name
HAVING COUNT(Booking.Booking_ID) > 2;



SELECT
    Customer.Customer_Name,
    Movie.Movie_Name,
    Booking.Total_Amount,
    Payment.Payment_Mode,
    Payment.Payment_Status
FROM Booking
JOIN Customer
    ON Booking.Customer_ID = Customer.Customer_ID
JOIN `Show`
    ON Booking.Show_ID = `Show`.Show_ID
JOIN Movie
    ON `Show`.Movie_ID = Movie.Movie_ID
JOIN Payment
    ON Booking.Payment_ID = Payment.Payment_ID;



SELECT
    Movie.Movie_Name,
    `Show`.Show_Date,
    `Show`.Show_Time,
    `Show`.Ticket_Price
FROM Movie
JOIN `Show`
    ON Movie.Movie_ID = `Show`.Movie_ID
WHERE `Show`.Ticket_Price = (
    SELECT MAX(Ticket_Price)
    FROM `Show`
);



SELECT
    Payment.Payment_Mode,
    COUNT(Booking.Booking_ID) AS Total_Bookings
FROM Payment
JOIN Booking
    ON Payment.Payment_ID = Booking.Payment_ID
GROUP BY Payment.Payment_Mode;



SELECT
    Screen.Screen_Type,
    AVG(`Show`.Ticket_Price) AS Average_Ticket_Price
FROM Screen
JOIN `Show`
    ON Screen.Screen_ID = `Show`.Screen_ID
GROUP BY Screen.Screen_Type;

-- trigger 1
DELIMITER //

CREATE TRIGGER check_payment
BEFORE UPDATE ON Booking
FOR EACH ROW
BEGIN
    DECLARE v_payment_status VARCHAR(20);

    IF NEW.Booking_Status = 'Confirmed'
       AND OLD.Booking_Status <> 'Confirmed' THEN

        SELECT Payment_Status
        INTO v_payment_status
        FROM Payment
        WHERE Payment_ID = NEW.Payment_ID;

        IF v_payment_status <> 'Paid' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
            'Booking cannot be confirmed until payment is completed';
        END IF;

    END IF;
END //

DELIMITER ;


-- test 1

UPDATE Booking
SET Booking_Status = 'Confirmed'
WHERE Booking_ID = 'B5Q8N';

SELECT Booking_ID, Booking_Status
FROM Booking
WHERE Booking_ID = 'B5Q8N';

UPDATE Payment
SET Payment_Status = 'Paid'
WHERE Payment_ID = 'P5T7N';



UPDATE Booking
SET Booking_Status = 'Pending'
WHERE Booking_ID = 'B5Q8N';

UPDATE Payment
SET Payment_Status = 'Pending'
WHERE Payment_ID = 'P5T7N';




--  trigger 2



DELIMITER //

CREATE TRIGGER update_seat_status
AFTER UPDATE ON Booking
FOR EACH ROW
BEGIN
    IF NEW.Booking_Status = 'Confirmed'
       AND OLD.Booking_Status <> 'Confirmed' THEN

        UPDATE Seat
        SET Seat_Status = 'Booked'
        WHERE Seat_ID = NEW.Seat_ID;

    ELSEIF NEW.Booking_Status = 'Cancelled'
       AND OLD.Booking_Status <> 'Cancelled' THEN

        UPDATE Seat
        SET Seat_Status = 'Available'
        WHERE Seat_ID = NEW.Seat_ID;

    END IF;
END //

DELIMITER ;

-- test 2

SELECT Booking_ID, Seat_ID, Booking_Status
FROM Booking
WHERE Booking_ID = 'B5Q8N';

SELECT Seat_ID, Seat_Status
FROM Seat
WHERE Seat_ID = (
    SELECT Seat_ID
    FROM Booking
    WHERE Booking_ID = 'B5Q8N'
);


-- trigger 3

DELIMITER //

CREATE TRIGGER prevent_double_booking
BEFORE INSERT ON Booking
FOR EACH ROW
BEGIN
    DECLARE existing_booking INT DEFAULT 0;

    IF NEW.Booking_Status IN ('Pending', 'Confirmed') THEN

        SELECT COUNT(*)
        INTO existing_booking
        FROM Booking
        WHERE Show_ID = NEW.Show_ID
          AND Seat_ID = NEW.Seat_ID
          AND Booking_Status IN ('Pending', 'Confirmed');

        IF existing_booking > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
            'This seat is already booked or reserved for this show';
        END IF;

    END IF;
END //

DELIMITER ;


-- test 3

SELECT Booking_ID, Show_ID, Seat_ID, Booking_Status
FROM Booking
ORDER BY Show_ID, Seat_ID;



