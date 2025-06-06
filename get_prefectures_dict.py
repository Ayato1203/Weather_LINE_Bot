import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_prefectures_dict() -> dict:
    
    config = {
        "host" : os.getenv("HOST"),
        "user" : "root",
        "password" : os.getenv("PASSWORD"),
        "database" : os.getenv("DATABASE"),
        "port" : int(os.getenv("PORT", 3306))
    }

    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    cursor.execute("SELECT name, name_en FROM prefectures")
    rows = cursor.fetchall()

    conn.close()

    return {name : name_en for name, name_en in rows}

