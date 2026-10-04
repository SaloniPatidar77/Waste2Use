import sqlite3

conn = sqlite3.connect("app.db")
cur = conn.cursor()

cur.executescript("""
INSERT INTO posts (title, content, waste_type, waste_amount, created_at, user_id)
VALUES
('Plastic Reuse Idea', 'Turning bottles into planters', 'Plastic', 2.5, '2025-10-20 10:00:00', 1),
('Metal Scrap Art', 'Art from scrap metal', 'Metal', 3.2, '2025-10-22 12:00:00', 1),
('Compost Tips', 'Organic composting', 'Organic', 1.5, '2025-10-23 11:30:00', 1),
('Glass Bottle Craft', 'Lamps from bottles', 'Glass', 4.0, '2025-10-25 14:45:00', 1);

INSERT INTO searches (query, search_date)
VALUES
('plastic reuse', '2025-10-20 09:00:00'),
('metal art', '2025-10-22 10:30:00'),
('organic compost', '2025-10-23 12:15:00'),
('bottle craft', '2025-10-25 15:00:00');
""")

conn.commit()
conn.close()
print("✅ Demo data inserted successfully!")
