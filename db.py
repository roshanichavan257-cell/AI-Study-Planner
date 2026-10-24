import os
import pymysql

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "22170")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "defaultdb"),
        cursorclass=pymysql.cursors.DictCursor,
        ssl={"ca": "ca.pem"}
    )
