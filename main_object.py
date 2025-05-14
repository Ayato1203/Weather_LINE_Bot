from fastapi import FastAPI, Request, Header, HTTPException
from contextlib import asynccontextmanager
import hashlib
import hmac
import base64
import os
import json
import httpx
from dotenv import load_dotenv
from get_prefectures_dict import get_prefectures_dict

load_dotenv()


class CityNameResolver:
    def __init__(self):
        self.prefectures_dict = self._expand_prefectures_dict(get_prefectures_dict())

    def _expand_prefectures_dict(self, ori_dict):
        new_dict = {}
        for jp_name, en_name in ori_dict.items():
            short_name = jp_name.replace("都", "").replace("道", "").replace("府", "").replace("県", "")
            new_dict[short_name] = en_name
        return new_dict

    def resolve(self, text):
        for keyword in ["の天気", " 天気", "天気", "てんき"]:
            if keyword in text:
                jp_city = text.replace(keyword, "").strip()
                return self.prefectures_dict.get(jp_city, jp_city)
        return ""


class WeatherService:
    def __init__(self, api_key):
        self.api_key = api_key

    async def get_weather(self, city):
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": self.api_key,
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
                    icon = self._get_weather_icon(weather)
                    return f"{city}の天気は「{weather}{icon}」、気温は{temp}℃です。"
                else:
                    return f"{city}の天気情報が取得できませんでした。ステータスコード: {response.status_code}"
            except Exception:
                return "天気情報の取得中にエラーが発生しました。"

    def _get_weather_icon(self, weather):
        if "晴" in weather:
            return "🌞"
        elif "曇" in weather or "雲" in weather:
            return "☁"
        elif "雨" in weather:
            return "☔"
        elif "雪" in weather:
            return "⛄"
        return ""


class LineBotHandler:
    def __init__(self, secret, access_token, weather_service, resolver):
        self.secret = secret
        self.access_token = access_token
        self.weather_service = weather_service
        self.resolver = resolver
        self.reply_url = "https://api.line.me/v2/bot/message/reply"

    def verify_signature(self, body: str, signature: str) -> bool:
        hash = hmac.new(self.secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
        signature = base64.b64decode(signature)
        return hmac.compare_digest(signature, hash)

    async def handle_event(self, event):
        if event["type"] == "message" and event["message"]["type"] == "text":
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]
            city_name = self.resolver.resolve(user_message)

            if city_name:
                weather_text = await self.weather_service.get_weather(city_name)
            else:
                weather_text = "都市名がわかりませんでした。例：「東京の天気」"

            await self.reply_to_user(reply_token, weather_text)

    async def reply_to_user(self, reply_token: str, message: str):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

        payload = {
            "replyToken": reply_token,
            "messages": [{"type": "text", "text": message}]
        }

        async with httpx.AsyncClient() as client:
            await client.post(self.reply_url, headers=headers, json=payload)


class WeatherBotApp:
    def __init__(self):
        self.app = FastAPI(lifespan=self.lifespan)
        self.resolver = CityNameResolver()
        self.weather_service = WeatherService(os.getenv("WEATHER_API_KEY"))
        self.handler = LineBotHandler(
            os.getenv("LINE_CHANNEL_SECRET"),
            os.getenv("LINE_CHANNEL_ACCESS_TOKEN"),
            self.weather_service,
            self.resolver
        )
        self.register_routes()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        yield

    def register_routes(self):
        @self.app.post("/webhook")
        async def webhook(request: Request, x_line_signature: str = Header(None)):
            body_bytes = await request.body()
            body_str = body_bytes.decode("utf-8")

            if not self.handler.verify_signature(body_str, x_line_signature):
                raise HTTPException(status_code=400, detail="Invalid signature")

            data = json.loads(body_str)
            events = data.get("events", [])
            for event in events:
                await self.handler.handle_event(event)

            return {"status": "ok"}


# 実行用のインスタンス
weather_bot_app = WeatherBotApp()
app = weather_bot_app.app