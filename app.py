from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    Emoji,
    VideoMessage,
    AudioMessage,
    LocationMessage,
    StickerMessage,
    ImageMessage,
    TemplateMessage,
    ButtonsTemplate,
    PostbackAction,
    ReplyMessageRequest,
    PushMessageRequest,
    BroadcastRequest,
    MulticastRequest
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,
    PostbackEvent,
    LocationMessageContent
)
import requests
import os

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

#加入好友事件
@line_handler.add(FollowEvent)
def handle_follow(event):
    print(f'Got {event.type} event')

#輸入訊息事件
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
@line_handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    latitude = event.message.latitude #取得使用者傳送位置的緯度
    longitude = event.message.longitude #取得使用者傳送位置的精度

    # 呼叫 OpenStreetMap Overpass API 查詢附近餐廳
    restaurants = get_nearby_restaurants(latitude, longitude)
    
    if restaurants:
        # 格式化餐廳清單
        reply_text = "附近的餐廳：\n" + "\n".join(restaurants)
    else:
        reply_text = "找不到附近的餐廳，請試試其他位置！"

    # 傳送回覆訊息
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

def get_nearby_restaurants(lat, lon):
    """使用 Overpass API 查詢附近餐廳"""
    overpass_url = "https://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    node[amenity=restaurant](around:1000,{lat},{lon});
    out;
    """
    
    response = requests.get(overpass_url, params={"data": overpass_query})
    data = response.json()
    
    restaurants = []
    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", "未知餐廳")  # 取得餐廳名稱
        res_lat = element["lat"]
        res_lon = element["lon"]
        
        # 建立 Google Maps 連結
        google_maps_link = f"https://www.google.com/maps/search/?api=1&query={res_lat},{res_lon}"
        restaurants.append(f"{name}：{google_maps_link}")

        if len(restaurants) >= 8:  # 最多回傳 5 間餐廳
            break

    return restaurants

if __name__ == "__main__":
    app.run()