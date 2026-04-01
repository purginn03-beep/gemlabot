"""
server.py
Веб-сервер для Render health checks
Запускается в отдельном потоке вместе с телеграм ботом
"""

import os
from flask import Flask, jsonify

app = Flask(__name__)


@app.route('/')
def index():
    """Главная страница"""
    return jsonify({
        "status": "ok",
        "message": "Telegram Redirect Bot is running",
        "service": "redirect_bot"
    })


@app.route('/health')
def health():
    """Health check endpoint для Render"""
    return jsonify({
        "status": "healthy",
        "bot": "active"
    })


def run_server():
    """Запуск сервера"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == "__main__":
    run_server()