# MCP-ChainBot

MCP-ChainBot is a multi-agent chatbot system that dynamically selects external tools through a communication protocol based on **A2A (Agent-to-Agent)** and **MCP (Multi-agent Communication Protocol)**. Built with Streamlit, it allows users to interact naturally while background agents handle weather inquiries, Wikipedia lookups, and currency exchange queries.

## 🧠 Architecture Overview

The architecture follows a modular multi-agent design:

- **UserAgent** receives the user's natural language input.
- Based on the intent, it selects one of the remote agents:
  - `WikiAgent`: queries Wikipedia.
  - `WeatherAgent`: fetches real-time weather information.
  - `ExchangeRateAgent`: retrieves the current exchange rate.
- Each agent communicates via MCP and fetches data through APIs, returning results to the user through the UI.

![Architecture]()

## 🚀 How to Run

Make sure your environment is set up as described below. Then run the following commands in separate terminals:

```bash
# Start MCP Host
python -m mcp.host

# Run Weather Agent server (port 8000)
uvicorn tools.weather_server:app --reload --port 8000

# Run Wiki Agent server (port 8001)
uvicorn tools.wiki_server:app --reload --port 8001

# Run Exchange Rate Agent server (port 8002)
uvicorn tools.exchange_server:app --reload --port 8002

# Run Chatbot UI
streamlit run app/main_app.py
```

## 🌐 API Sources
This project uses the following APIs:

GroqCloud API – For LLM inference

OpenWeather API – For weather information

OpenExchangeRates API – For currency conversion

Ensure that your .env file includes the API keys for the services above.

## Setting Virtual Environment
1. Create a virtual environment:
    ```bash
    python3 -m venv venv
    ```

2. Activate the virtual environment:
    - macOS/Linux:
    ```bash
    source venv/bin/activate
    ```

- Windows:
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. After you're done:
    ```bash
    deactivate
    ```