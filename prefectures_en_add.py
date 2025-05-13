import pandas as pd
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

df = pd.read_csv("prefectures_en.csv")

config = {
    "host" : os.getenv("HOST"),
    "user" : "root",
    "password" : os.getenv("PASSWORD"),
    "database" : os.getenv("DATABASE")
}

conn = mysql.connector.connect(**config)
cursor = conn.cursor()

cursor.execute("""
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE table_schema = %s AND table_name = %s AND column_name = %s
""", (config['database'], 'prefectures', 'name_en'))

(column_exists,) = cursor.fetchone()

if column_exists == 0:
    print("'name_en'カラムを追加します")
    cursor.execute("ALTER TABLE prefectures ADD COLUMN name_en VARCHAR(100)")
else:
    print("'name_en'カラムは既に存在します")

update_sql = "UPDATE prefectures SET name_en = %s WHERE id = %s"
for _, row in df.iterrows():
    cursor.execute(update_sql, (row["name_en"], int(row["id"])))
print("成功")


conn.commit()
cursor.close()
conn.close()