import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

TRASH_CRITERIA = {
    "min_impressions": 100,      # Минимум показов для анализа
    "max_ctr": 0.1,              # CTR ниже 0.1% - подозрительно
    "min_cost_without_conv": 500, # Потрачено более 500р без конверсий
    "max_conversion_rate": 0.5,   # Конверсия ниже 0.5%
}

COLUMN_MAPPINGS = {
    "placement": ["Площадка", "Название площадки", "placement", "Placement"],
    "impressions": ["Показы", "impressions", "Impressions"],
    "clicks": ["Клики", "clicks", "Clicks"],
    "cost": ["Расход", "Стоимость", "cost", "Cost", "Расход (руб.)"],
    "conversions": ["Конверсии", "conversions", "Conversions", "Целевые действия"],
}
