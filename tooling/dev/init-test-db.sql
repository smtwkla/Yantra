-- Test databases (runs once on first container init).
-- MARIADB_USER (vel_yantra_master) already owns the main DB.
-- The backend tests create their own databases, one per test run and pytest-xdist worker
-- (backend/tests/db_names.py: vel_yantra_test_<run>_<worker>, and vel_yantra_upgrade_<run>_<worker>
-- for the migration upgrade tests); the user may create any database matching these patterns.
-- tooling/run-backend-tests.bat makes the same grants on an existing container.
GRANT ALL PRIVILEGES ON `vel\_yantra\_test\_%`.* TO 'vel_yantra_master'@'%';
GRANT ALL PRIVILEGES ON `vel\_yantra\_upgrade\_%`.* TO 'vel_yantra_master'@'%';
-- The browser tests' database (S024; tooling/run-e2e-tests.bat also creates it on an existing container)
CREATE DATABASE IF NOT EXISTS vel_yantra_e2e CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON vel_yantra_e2e.* TO 'vel_yantra_master'@'%';
FLUSH PRIVILEGES;
