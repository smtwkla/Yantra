-- Create the test database (runs once on first container init).
-- MARIADB_USER (vel_yantra_master) already owns the main DB;
-- this script creates a second DB for automated tests, and a third for the browser
-- tests (S024; tooling/run-e2e-tests.bat also creates it on an existing container).

CREATE DATABASE IF NOT EXISTS vel_yantra_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON vel_yantra_test.* TO 'vel_yantra_master'@'%';
CREATE DATABASE IF NOT EXISTS vel_yantra_e2e CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON vel_yantra_e2e.* TO 'vel_yantra_master'@'%';
FLUSH PRIVILEGES;
