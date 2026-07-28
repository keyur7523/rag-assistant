import sqlite3

orders_data = [
    (12345, "Alice Chen",    "Desk Lamp",               "2026-07-01", "in transit", "2026-07-08"),
    (12346, "Marcus Webb",   "Wireless Keyboard",       "2026-07-14", "delivered",  "2026-07-18"),
    (12347, "Priya Raman",   "Standing Desk Converter", "2026-06-02", "delivered",  "2026-06-08"),
    (12348, "Daniel Okafor", "USB-C Hub",               "2026-07-22", "in transit", "2026-07-29"),
    (12349, "Sofia Reyes",   "Monitor Arm",             "2026-07-10", "delivered",  "2026-07-15"),
]

def create_my_table():
    connection = sqlite3.connect("orders.db")
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            item TEXT NOT NULL,
            order_date DATE NOT NULL,
            status TEXT NOT NULL,
            expected_delivery DATE NOT NULL
        );
        """
    );

    connection.commit()
    connection.close()
    print(f"Table orders created successfully!")

def insert_orders():
    connection = sqlite3.connect("orders.db")
    cursor = connection.cursor()
    cursor.executemany(
        """
        INSERT INTO orders (order_id, customer_name, item, order_date, status, expected_delivery)
        VALUES (?, ?, ?, ?, ?, ?);
        """, orders_data
    );
    connection.commit()
    connection.close()
    print(f"Values inserted in the orders successfully!")

def test_orders():
    connection = sqlite3.connect("orders.db")
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT * from orders;
        """
    );
    connection.commit()
    connection.close()

if __name__ == "__main__":
    create_my_table()
    insert_orders()
    test_orders()