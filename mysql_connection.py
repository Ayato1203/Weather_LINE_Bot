import pandas as pd
import mysql.connector
import os
from dotenv import load_dotenv

###テーブル作成済み####

load_dotenv()

#元データの読み込み
df = pd.read_csv("prefectures_data.csv")

# 都道府県データの準備
prefecture_df = df[["都道府県名", "都道府県名(カナ)"]].drop_duplicates().dropna().reset_index(drop=True)
prefecture_df["id"] = prefecture_df.index + 1

# 区市町村データの準備
municipality_df = df[["都道府県名", "市区町村名", "市区町村名(カナ)"]].dropna()
municipality_df = municipality_df.merge(prefecture_df, on="都道府県名")
municipality_df = municipality_df.rename(columns={"市区町村名": "name", "市区町村名(カナ)" : "name_kana"})

# MySQL接続情報を取得
config = {
    "host" : os.getenv("HOST"),
    "user" : "root",
    "password" : os.getenv("PASSWORD"),
    "database" : os.getenv("DATABASE")
}

# 接続・書込み
conn = mysql.connector.connect(**config)
cursor = conn.cursor()

for _, row in prefecture_df.iterrows():
    cursor.execute("INSERT INTO prefectures (id, name, name_kana) VALUES (%s, %s, %s)",
                   (row["id"], row["都道府県名"], row["都道府県名(カナ)"]))
    
for _, row in municipality_df.iterrows():
    cursor.execute("INSERT INTO municipalities (prefecture_id, name, name_kana) VALUES (%s, %s, %s)",
                   (row["id"], row["name"], row["name_kana"]))


conn.commit()
cursor.close()
conn.close()
