CREATE DATABASE IF NOT EXISTS stock_trading_simulator;

USE stock_trading_simulator;


-- =========================
-- USERS
-- =========================

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Trader', 'Regulator', 'Admin') NOT NULL DEFAULT 'Trader',
    cash_balance DECIMAL(12,2) NOT NULL DEFAULT 1000.00,
    reserved_cash DECIMAL(12,2) NOT NULL DEFAULT 0.00
);


-- =========================
-- STOCKS
-- =========================

CREATE TABLE stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL UNIQUE,
    company_name VARCHAR(100) NOT NULL,
    current_price DECIMAL(12,2) NOT NULL,
    total_supply INT NOT NULL DEFAULT 1000,
    available_supply INT NOT NULL DEFAULT 1000,
    volatility DECIMAL(5,2) NOT NULL DEFAULT 5.00
);


-- =========================
-- STOCK PRICE HISTORY
-- =========================

CREATE TABLE stock_price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_id INT NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_price_history_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id)
);


-- =========================
-- PORTFOLIOS
-- =========================

CREATE TABLE portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    stock_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    reserved_quantity INT NOT NULL DEFAULT 0,
    avg_buy_price DECIMAL(12,2) NOT NULL DEFAULT 0.00,

    CONSTRAINT fk_portfolio_user
        FOREIGN KEY (user_id) REFERENCES users(id),

    CONSTRAINT fk_portfolio_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id),

    CONSTRAINT unique_user_stock
        UNIQUE (user_id, stock_id)
);


-- =========================
-- ORDERS
-- =========================

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    stock_id INT NOT NULL,
    order_type ENUM('BUY', 'SELL') NOT NULL,
    order_source ENUM('MARKET', 'PLAYER') NOT NULL DEFAULT 'PLAYER',
    quantity INT NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    market_fee DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    status ENUM('OPEN', 'EXECUTED', 'CANCELLED') NOT NULL DEFAULT 'OPEN',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accepted_by_user_id INT NULL,
    accepted_at DATETIME NULL,
    executed_at DATETIME NULL,

    CONSTRAINT fk_order_user
        FOREIGN KEY (user_id) REFERENCES users(id),

    CONSTRAINT fk_order_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id),

    CONSTRAINT fk_order_accepted_by
        FOREIGN KEY (accepted_by_user_id) REFERENCES users(id)
);


-- =========================
-- AUDIT LOG
-- =========================

CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT NULL,

    CONSTRAINT fk_audit_user
        FOREIGN KEY (user_id) REFERENCES users(id)
);


-- =========================
-- GAME STATE
-- =========================

CREATE TABLE game_state (
    id INT AUTO_INCREMENT PRIMARY KEY,
    current_round INT NOT NULL DEFAULT 1,
    time_remaining INT NOT NULL DEFAULT 0,
    status ENUM('ACTIVE', 'PAUSED', 'ENDED') NOT NULL DEFAULT 'ACTIVE',
    starting_capital DECIMAL(12,2) NOT NULL DEFAULT 100000.00,
    market_fee_percent DECIMAL(5,2) NOT NULL DEFAULT 5.00
);