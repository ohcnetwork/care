from plugs.manager import PlugManager
from plugs.plug import Plug

plugs = [
    Plug(
        name="care_whatsapp_bot",
        package_name="./care_whatsapp_bot",
        version="",
        configs={
            "WHATSAPP_ACCESS_TOKEN": "EAFYi1HZB6eFQBPDpuWeyzIoTVGKMTj9JvZCXxsHwjmu5QYRR0EdN62EfpjkoQKSOZATJXA1m2bF5eAhkZAi9NXsZAp0YG0KFZCoOiWUcUBARAKbs8LhepWFxCKKcmjT3wmXzII7uDZBZBMFh8gX0roBqzybYfjFuMr9mpYLTqoxZAZCqivvYfWDhnouqHZCj9T82TIghQZDZD",
            "WHATSAPP_VERIFY_TOKEN": "GSoC2025CareBot",
            "WHATSAPP_PHONE_NUMBER_ID": "651347521403933",
            "WHATSAPP_WEBHOOK_URL": "http://localhost:8000/api/care_whatsapp_bot/webhook/"
        }
    )
]

manager = PlugManager(plugs)
