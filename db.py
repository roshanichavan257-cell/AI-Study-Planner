import os
import pymysql

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST","sql12.freesqldatabase.com"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER","sql12839417"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "sql12839417"),
        cursorclass=pymysql.cursors.DictCursor,
    )
