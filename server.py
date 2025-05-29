from flask import Flask
from threading import Thread
import main  # Això executa el teu codi principal

app = Flask(__name__)

@app.route("/")
def home():
    return "Enjoyability script executat!"

def run():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run).start()
