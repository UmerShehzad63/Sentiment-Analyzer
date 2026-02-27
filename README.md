📈 AI Stock Sentiment Analyzer
An advanced, real-time stock market sentiment analysis dashboard that bridges the gap between financial news and actionable market insights. Powered by Groq's LPU Inference and Streamlit.

🚀 Overview
The AI Stock Sentiment Analyzer is a high-performance tool designed for traders and investors to gauge market sentiment instantly. By scraping the latest financial news from Finviz and leveraging Large Language Models (LLMs) via the Groq Cloud API, the application classifies news sentiment as Bullish, Bearish, or Neutral, providing a clear visual representation of market mood alongside real-time stock metrics.

✨ Key Features
Real-Time Data: Fetches live stock prices and historical performance metrics using yfinance.
Intelligent Sentiment Analysis: Uses Groq-powered LLMs for lightning-fast and accurate sentiment classification of financial headlines.
Automated News Scraping: Programmatically extracts the latest news from Finviz for any given ticker symbol.
Interactive Visualizations: Dynamic charts and sentiment distributions powered by Plotly.
Smart Ticker Search: Robust search functionality that converts company names to ticker symbols automatically.
Modern dashboard: A sleek, professional UI with custom CSS styling and responsive design.
🛠️ Tech Stack
Language: Python 3.10+
Frontend: Streamlit
AI Engine: Groq Cloud API (LPU Inference)
Financial Data: yfinance
Web Scraping: BeautifulSoup4 & Requests
Visuals: Plotly
Environment: python-dotenv, VS Code Dev Containers
📁 File Structure
text
├── .devcontainer/      # Dev container configurations for standardized environment
├── app.py              # Main application logic & Streamlit UI
├── requirements.txt    # Python dependencies
└── .env               # Environment variables (API Keys)
⚙️ Installation & Setup
Clone the Repository

bash
git clone https://github.com/UmerShehzad63/Sentiment-Analyzer.git
cd Sentiment-Analyzer
Set Up Environment Variables Create a .env file in the root directory and add your Groq API key:

env
GROQ_API_KEY=your_groq_api_key_here
Install Dependencies

bash
pip install -r requirements.txt
Run the Application

bash
streamlit run app.py
🛡️ Privacy & Security
This application requires a Groq API Key. Ensure your .env file is included in your .gitignore to prevent leaking sensitive credentials.

Created by Umer Shehzad
