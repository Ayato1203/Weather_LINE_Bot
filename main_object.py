from fastapi import FastAPI, Request, Header, HTTPException
import hashlib, hmac, os, json, base64
from dotenv import load_dotenv
import httpx

load_dotenv()

app = FastAPI()

class LineBot:
    def __init__(self):
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.weather_api_key = os.getenv("WEATHER_API_KEY")
        self.reply_url = "https://api.line.me/v2/bot/message/reply"

    def verify_signature(self, body: str, signature: str) -> bool:
        hash = hmac.new(self.channel_secret.encode(), body.encode(), hashlib.sha256).digest()
        try:
            signature_bytes = base64.b64decode(signature)
        except Exception:
            return False
        return hmac.compare_digest(signature_bytes, hash)

    def extract_city_name(self, text: str) -> str:
        for keyword in ["の天気", " 天気", "天気", "てんき"]:
            if keyword in text:
                return text.replace(keyword, "").strip()
        return ""

    async def get_weather(self, city: str) -> str:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": self.weather_api_key,
            "units": "metric",
            "lang": "ja"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                data = response.json()
                if response.status_code == 200:
                    weather = data["weather"][0]["description"]
                    temp = data["main"]["temp"]
                    emoji = self.get_weather_emoji(weather)
                    return f"{city}の天気は「{weather}{emoji}」、気温は{temp}℃です。"
                else:
                    return f"{city}の天気情報が取得できませんでした。コード: {response.status_code}"
            except Exception:
                return "天気情報の取得中にエラーが発生しました。"

    def get_weather_emoji(self, weather: str) -> str:
        if "晴" in weather: return "🌞"
        if "曇" in weather: return "☁"
        if "雨" in weather: return "☔"
        if "雪" in weather: return "⛄"
        return ""

    async def reply_to_user(self, reply_token: str, message: str):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }
        payload = {
            "replyToken": reply_token,
            "messages": [{"type": "text", "text": message}]
        }
        async with httpx.AsyncClient() as client:
            await client.post(self.reply_url, headers=headers, json=payload)

    async def handle_event(self, event: dict):
        if event["type"] == "message" and event["message"]["type"] == "text":
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]

            city = self.extract_city_name(user_message)
            if city:
                weather_text = await self.get_weather(city)
            else:
                weather_text = "都市名がわかりませんでした。例：「東京の天気」"

            await self.reply_to_user(reply_token, weather_text)

# グローバルインスタンスを作成
line_bot = LineBot()

@app.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    body_str = body.decode()

    if not line_bot.verify_signature(body_str, x_line_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = json.loads(body_str)
    events = data.get("events", [])

    for event in events:
        await line_bot.handle_event(event)

    return {"status": "ok"}