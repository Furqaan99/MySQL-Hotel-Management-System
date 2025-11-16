SET @@session.sql_mode = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

DROP DATABASE IF EXISTS hotel_db;
CREATE DATABASE hotel_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hotel_db;

-- =========================
-- 2. TABLE CREATION
-- =========================

CREATE TABLE Hotel (
  hotel_id INT AUTO_INCREMENT PRIMARY KEY,
  hotel_name VARCHAR(150) NOT NULL,
  address TEXT,
  city VARCHAR(100),
  country VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE Room (
  room_id INT AUTO_INCREMENT PRIMARY KEY,
  hotel_id INT NOT NULL,
  room_number VARCHAR(20) NOT NULL,
  room_type ENUM('Single','Double','Twin','Suite','Deluxe') NOT NULL,
  price_per_night DECIMAL(10,2) NOT NULL CHECK (price_per_night >= 0),
  status ENUM('Available','Booked','Maintenance') NOT NULL DEFAULT 'Available',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_room_hotel FOREIGN KEY (hotel_id)
    REFERENCES Hotel(hotel_id) ON DELETE CASCADE,
  UNIQUE KEY uk_hotel_roomnum (hotel_id, room_number)
) ENGINE=InnoDB;

CREATE TABLE Guest (
  guest_id INT AUTO_INCREMENT PRIMARY KEY,
  guest_name VARCHAR(150) NOT NULL,
  email VARCHAR(150) UNIQUE,
  phone VARCHAR(30),
  password_hash CHAR(64) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE Reservation (
  reservation_id INT AUTO_INCREMENT PRIMARY KEY,
  guest_id INT NOT NULL,
  room_id INT NOT NULL,
  check_in_date DATE NOT NULL,
  check_out_date DATE NOT NULL,
  booking_status ENUM('Active','CheckedIn','CheckedOut','Cancelled') NOT NULL DEFAULT 'Active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_res_guest FOREIGN KEY (guest_id) REFERENCES Guest(guest_id) ON DELETE CASCADE,
  CONSTRAINT fk_res_room FOREIGN KEY (room_id) REFERENCES Room(room_id) ON DELETE RESTRICT,
  CONSTRAINT chk_dates CHECK (check_out_date > check_in_date)
) ENGINE=InnoDB;

CREATE TABLE Billing (
  billing_id INT AUTO_INCREMENT PRIMARY KEY,
  reservation_id INT NOT NULL UNIQUE,
  billed_amount DECIMAL(12,2) NOT NULL,
  paid_amount DECIMAL(12,2) DEFAULT 0,
  billing_status ENUM('Unpaid','Partial','Paid','Refunded') NOT NULL DEFAULT 'Unpaid',
  payment_method ENUM('Card','Cash','Online') DEFAULT 'Card',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_bill_res FOREIGN KEY (reservation_id) REFERENCES Reservation(reservation_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE PaymentDetails (
  payment_id INT AUTO_INCREMENT PRIMARY KEY,
  billing_id INT NOT NULL,
  card_holder VARCHAR(150),
  card_number_enc VARBINARY(512),
  card_expiry CHAR(7),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pay_bill FOREIGN KEY (billing_id) REFERENCES Billing(billing_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Flask login-related table
CREATE TABLE User (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin','manager','analyst') NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =========================
-- 3. SAMPLE DATA INSERTION
-- =========================

INSERT INTO Hotel (hotel_name, address, city, country) VALUES
('Seaside Inn', '123 Beach Ave', 'Karachi', 'Pakistan'),
('Mountain View Hotel', '88 Hill St', 'Lahore', 'Pakistan');

INSERT INTO Room (hotel_id, room_number, room_type, price_per_night) VALUES
(1, '101', 'Single', 35.00),
(1, '102', 'Double', 50.00),
(1, '201', 'Suite', 120.00),
(2, '10A', 'Double', 60.00),
(2, '11B', 'Deluxe', 95.00);

INSERT INTO Guest (guest_name, email, phone, password_hash) VALUES
('Ali Khan', 'ali.khan@example.com', '+92-300-0000001', SHA2('guestpassword1',256)),
('Sara Ahmed', 'sara.ahmed@example.com', '+92-300-0000002', SHA2('guestpassword2',256));

INSERT INTO Reservation (guest_id, room_id, check_in_date, check_out_date) VALUES
(1, 1, '2025-11-01', '2025-11-03'),
(2, 3, '2025-12-15', '2025-12-20');

INSERT INTO Billing (reservation_id, billed_amount, paid_amount, billing_status, payment_method) VALUES
(1, 70.00, 0.00, 'Unpaid','Card'),
(2, 600.00, 600.00, 'Paid','Online');

SET @aes_key = 'your_aes_key_here';
INSERT INTO PaymentDetails (billing_id, card_holder, card_number_enc, card_expiry) VALUES
(1, 'Ali Khan', AES_ENCRYPT('4111111111111111', @aes_key), '12/2027'),
(2, 'Sara Ahmed', AES_ENCRYPT('5555555555554444', @aes_key), '03/2026');

-- Staff table for display
CREATE TABLE Staff (
  staff_id INT AUTO_INCREMENT PRIMARY KEY,
  hotel_id INT,
  staff_name VARCHAR(150),
  role ENUM('Admin','Manager','Reception') NOT NULL DEFAULT 'Reception',
  email VARCHAR(150) UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_hotel_id FOREIGN KEY (hotel_id) REFERENCES Hotel(hotel_id) ON DELETE CASCADE
) ENGINE=InnoDB;

INSERT INTO Staff (staff_name, role, email) VALUES
('Ayesha Malik', 'Admin', 'ayesha@hotel.com'),
('Bilal Raza', 'Manager', 'bilal@hotel.com');

-- =========================
-- 4. USER AUTHENTICATION (FOR FLASK)
-- =========================
-- Insert app users with SHA2 hash to match form passwords (or bcrypt later)
INSERT INTO User (username, password_hash, role) VALUES
('admin_user', SHA2('AdminPass123!',256), 'admin'),
('manager_user', SHA2('ManagerPass123!',256), 'manager'),
('analyst_user', SHA2('AnalystPass123!',256), 'analyst');

-- =========================
-- 5. MYSQL DATABASE USERS & ROLES
-- =========================
-- Drop and recreate users with proper privileges
DROP USER IF EXISTS 'admin_user'@'localhost';
DROP USER IF EXISTS 'manager_user'@'localhost';
DROP USER IF EXISTS 'analyst_user'@'localhost';
DROP USER IF EXISTS 'app_user'@'localhost';

-- Create users
CREATE USER 'admin_user'@'localhost' IDENTIFIED BY 'AdminPass123!';
CREATE USER 'manager_user'@'localhost' IDENTIFIED BY 'ManagerPass123!';
CREATE USER 'analyst_user'@'localhost' IDENTIFIED BY 'AnalystPass123!';
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'AppPass123!';

-- Grant privileges to app_user (this is the user your Flask app uses)
GRANT SELECT, INSERT, UPDATE, DELETE ON hotel_db.* TO 'app_user'@'localhost';

-- Grant specific privileges based on roles
GRANT ALL PRIVILEGES ON hotel_db.* TO 'admin_user'@'localhost';

GRANT SELECT, INSERT, UPDATE, DELETE ON hotel_db.Reservation TO 'manager_user'@'localhost';
GRANT SELECT, UPDATE ON hotel_db.Billing TO 'manager_user'@'localhost';
GRANT SELECT ON hotel_db.Room TO 'manager_user'@'localhost';
GRANT SELECT ON hotel_db.Guest TO 'manager_user'@'localhost';
GRANT SELECT ON hotel_db.Hotel TO 'manager_user'@'localhost';

GRANT SELECT ON hotel_db.* TO 'analyst_user'@'localhost';

FLUSH PRIVILEGES;

-- Grant all necessary privileges to app_user
GRANT SELECT, INSERT, UPDATE, DELETE ON hotel_db.* TO 'app_user'@'localhost';
FLUSH PRIVILEGES;