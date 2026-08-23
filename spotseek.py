# simple run:
# python3 -m uvicorn spotseek:app --host 127.0.0.1 --port 3006


from my_imports import *
from bot_handlers import register_handlers

app = FastAPI()

# Change bot initialization to use AsyncTeleBot
bot = async_bot

# register bot handlers
register_handlers(bot)

# --- FastAPI webhook endpoint ---
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = types.Update.de_json(data)
    # Process update in background to respond 200 OK immediately
    asyncio.create_task(bot.process_new_updates([update]))
    return Response(status_code=200, content="OK")

# --- Startup event to set webhook ---
@app.on_event("startup")
async def on_startup():
    # Remove old webhook if any
    await asyncio.sleep(5)
    await bot.remove_webhook()
    # Set new webhook
    await asyncio.sleep(5)
    await bot.set_webhook(
        url=WEBHOOK_URL,
        max_connections=100,
        drop_pending_updates=False,
        secret_token=WEBHOOK_SECRET_TOKEN
    )
    print("Webhook set to:", WEBHOOK_URL)