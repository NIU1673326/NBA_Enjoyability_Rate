from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Enjoyability script is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    run()
