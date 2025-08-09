-- Sample data for testing Analyst Agent
-- This creates a simple e-commerce database with sales, products, and customers

-- Create tables
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    segment TEXT CHECK (segment IN ('Premium', 'Standard', 'Basic')),
    signup_date DATE,
    country TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    price DECIMAL(10,2),
    cost DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date DATE,
    status TEXT CHECK (status IN ('pending', 'completed', 'cancelled', 'shipped')),
    total_amount DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER,
    unit_price DECIMAL(10,2)
);

-- Insert sample customers
INSERT OR REPLACE INTO customers (id, name, email, segment, signup_date, country) VALUES
(1, 'Alice Johnson', 'alice@email.com', 'Premium', '2023-01-15', 'USA'),
(2, 'Bob Smith', 'bob@email.com', 'Standard', '2023-02-20', 'Canada'),
(3, 'Carol Williams', 'carol@email.com', 'Premium', '2023-03-10', 'UK'),
(4, 'David Brown', 'david@email.com', 'Basic', '2023-04-05', 'USA'),
(5, 'Emma Davis', 'emma@email.com', 'Standard', '2023-05-12', 'Australia'),
(6, 'Frank Miller', 'frank@email.com', 'Premium', '2023-06-18', 'Germany'),
(7, 'Grace Wilson', 'grace@email.com', 'Basic', '2023-07-22', 'France'),
(8, 'Henry Taylor', 'henry@email.com', 'Standard', '2023-08-30', 'Japan'),
(9, 'Ivy Anderson', 'ivy@email.com', 'Premium', '2023-09-14', 'USA'),
(10, 'Jack Thomas', 'jack@email.com', 'Basic', '2023-10-25', 'Canada');

-- Insert sample products
INSERT OR REPLACE INTO products (id, name, category, price, cost) VALUES
(1, 'Wireless Headphones', 'Electronics', 199.99, 80.00),
(2, 'Smart Phone', 'Electronics', 699.99, 350.00),
(3, 'Laptop Computer', 'Electronics', 1299.99, 800.00),
(4, 'Coffee Maker', 'Appliances', 89.99, 45.00),
(5, 'Running Shoes', 'Sports', 129.99, 60.00),
(6, 'Yoga Mat', 'Sports', 39.99, 15.00),
(7, 'Desk Chair', 'Furniture', 249.99, 120.00),
(8, 'Standing Desk', 'Furniture', 399.99, 200.00),
(9, 'Water Bottle', 'Accessories', 24.99, 8.00),
(10, 'Bluetooth Speaker', 'Electronics', 79.99, 35.00);

-- Insert sample orders (last 6 months)
INSERT OR REPLACE INTO orders (id, customer_id, order_date, status, total_amount) VALUES
-- January 2024
(1, 1, '2024-01-10', 'completed', 329.98),
(2, 2, '2024-01-15', 'completed', 699.99),
(3, 3, '2024-01-20', 'completed', 1299.99),
-- February 2024  
(4, 4, '2024-02-05', 'completed', 89.99),
(5, 5, '2024-02-14', 'completed', 169.98),
(6, 6, '2024-02-28', 'completed', 649.98),
-- March 2024
(7, 7, '2024-03-08', 'completed', 39.99),
(8, 8, '2024-03-15', 'completed', 249.99),
(9, 9, '2024-03-22', 'shipped', 479.98),
-- April 2024
(10, 10, '2024-04-03', 'completed', 104.98),
(11, 1, '2024-04-12', 'completed', 1299.99),
(12, 2, '2024-04-20', 'completed', 129.99),
-- May 2024
(13, 3, '2024-05-05', 'completed', 79.99),
(14, 4, '2024-05-18', 'shipped', 399.99),
(15, 5, '2024-05-25', 'completed', 199.99),
-- June 2024
(16, 6, '2024-06-02', 'completed', 89.99),
(17, 7, '2024-06-15', 'completed', 369.98),
(18, 8, '2024-06-28', 'pending', 129.99),
-- July 2024
(19, 9, '2024-07-08', 'completed', 699.99),
(20, 10, '2024-07-15', 'completed', 64.98),
(21, 1, '2024-07-25', 'shipped', 1549.98);

-- Insert order items
INSERT OR REPLACE INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
-- Order 1: Wireless Headphones + Running Shoes
(1, 1, 1, 1, 199.99), (2, 1, 5, 1, 129.99),
-- Order 2: Smart Phone
(3, 2, 2, 1, 699.99),
-- Order 3: Laptop
(4, 3, 3, 1, 1299.99),
-- Order 4: Coffee Maker
(5, 4, 4, 1, 89.99),
-- Order 5: Running Shoes + Yoga Mat
(6, 5, 5, 1, 129.99), (7, 5, 6, 1, 39.99),
-- Order 6: Smart Phone + Headphones + Speaker
(8, 6, 2, 1, 699.99), (9, 6, 1, 1, 199.99), (10, 6, 10, 1, 79.99),
-- Order 7: Yoga Mat
(11, 7, 6, 1, 39.99),
-- Order 8: Desk Chair
(12, 8, 7, 1, 249.99),
-- Order 9: Standing Desk + Water Bottle
(13, 9, 8, 1, 399.99), (14, 9, 9, 2, 24.99),
-- Order 10: Water Bottle + Speaker
(15, 10, 9, 2, 24.99), (16, 10, 10, 1, 79.99),
-- Order 11: Laptop
(17, 11, 3, 1, 1299.99),
-- Order 12: Running Shoes
(18, 12, 5, 1, 129.99),
-- Order 13: Speaker
(19, 13, 10, 1, 79.99),
-- Order 14: Standing Desk
(20, 14, 8, 1, 399.99),
-- Order 15: Headphones
(21, 15, 1, 1, 199.99),
-- Order 16: Coffee Maker
(22, 16, 4, 1, 89.99),
-- Order 17: Desk Chair + Running Shoes
(23, 17, 7, 1, 249.99), (24, 17, 5, 1, 129.99),
-- Order 18: Running Shoes
(25, 18, 5, 1, 129.99),
-- Order 19: Smart Phone
(26, 19, 2, 1, 699.99),
-- Order 20: Water Bottle + Yoga Mat
(27, 20, 9, 1, 24.99), (28, 20, 6, 1, 39.99),
-- Order 21: Laptop + Smart Phone
(29, 21, 3, 1, 1299.99), (30, 21, 2, 1, 699.99);

-- Create useful views for analysis
CREATE VIEW IF NOT EXISTS sales_summary AS
SELECT 
    DATE(o.order_date) as order_date,
    strftime('%Y-%m', o.order_date) as month,
    strftime('%Y', o.order_date) as year,
    o.id as order_id,
    c.id as customer_id,
    c.name as customer_name,
    c.segment as customer_segment,
    c.country,
    p.id as product_id,
    p.name as product_name,
    p.category,
    oi.quantity,
    oi.unit_price,
    (oi.quantity * oi.unit_price) as line_total,
    o.total_amount as order_total,
    o.status as order_status
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id;

-- Display sample data for verification
SELECT 'Total customers:' as metric, COUNT(*) as value FROM customers
UNION ALL
SELECT 'Total products:', COUNT(*) FROM products  
UNION ALL
SELECT 'Total orders:', COUNT(*) FROM orders
UNION ALL
SELECT 'Total revenue:', printf('$%.2f', SUM(total_amount)) FROM orders WHERE status = 'completed'; 