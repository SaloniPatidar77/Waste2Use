from app import db, Post
from sqlalchemy.exc import OperationalError

try:
    db.engine.execute('ALTER TABLE post ADD COLUMN image VARCHAR(200)')
    print("Column 'image' added successfully!")
except OperationalError as e:
    print("Error:", e)
