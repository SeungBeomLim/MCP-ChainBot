# utils/settings.py

import os
from dotenv import load_dotenv

load_dotenv()

# OpenWeatherMap API key
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# Wikipedia API doesn’t need a key