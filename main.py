from fastapi import FastAPI, Request, Header, HTTPException
import hashlib
import hmac
import os
import json
from dotenv import load_dotenv
import httpx
import base64

load_dotenv()

app = FastAPI()

LINE_CHANNAL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"


def verify_signature(body : str, signature : str) -> bool:
    hash = hmac.new(LINE_CHANNAL_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    # signatureをbyteに変換
    signature = base64.b64decode(signature)
    expected_signature = hmac.compare_digest(signature, hash)
    return expected_signature

@app.post("/webhook")
async def webhook(
    request : Request,
    x_line_signature : str = Header(None)
):
    body = await request.body()
    body_str = body.decode("utf-8")

    if not verify_signature(body_str, x_line_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = json.loads(body_str)
    events = data.get("events", [])

    for event in events:
        if event["type"] == "message" and event["message"]["type"] == "text":
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]

            city_name = extract_city_name(user_message)
            if city_name:
                weather_text = await get_weather(city_name)
                await reply_to_user(reply_token, weather_text)
            else:
                await reply_to_user(reply_token, "都市名がわかりませんでした。例：「東京の天気」")
    
    return {"status" : "ok"}
        

def extract_city_name(text : str) -> str:
    for keyword in ["の天気", " 天気", "天気", "てんき"]:
        if keyword in text:
            return text.replace(keyword, "").strip()
    return ""


async def get_weather(city : str) -> str:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q" : city,
        "appid" : WEATHER_API_KEY,
        "units" : "metric",
        "lang" :"ja"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            data = response.json()
            print(data)
            if response.status_code == 200:
                weather = data["weather"][0]["description"]
                temp = data["main"]["temp"]
                if "晴" in weather:
                    return f"{city}の天気は「{weather}🌞」、気温は{temp}℃です。"
                elif "曇" in weather:
                    return f"{city}の天気は「{weather}☁」、気温は{temp}℃です。"
                elif "雨" in weather:
                    return f"{city}の天気は「{weather}☔」、気温は{temp}℃です。"
                elif "雪" in weather:
                    return f"{city}の天気は「{weather}⛄」、気温は{temp}℃です。"
                else:
                    return f"{city}の天気は「{weather}」、気温は{temp}℃です。"
            else:
                return f"{city}の天気情報が取得できませんでした。ステータスコード: {response.status_code} メッセージ: {response.text}"
        except Exception as e:
            return "天気情報の取得中にエラーが発生しました。"        


async def reply_to_user(reply_token : str, message : str):
    headers = {
        "Content-Type" : "application/json",
        "Authorization" : f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    payload = {
        "replyToken" : reply_token,
        "messages" : [
            {
                "type" : "text",
                "text" : message
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        await client.post(LINE_REPLY_URL, headers=headers, json=payload)



