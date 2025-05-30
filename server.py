from flask import Flask
import subprocess

app = Flask(__name__)

@app.route('/')
def home():
    return "UptimeRobot is keeping me awake!"

@app.route('/run-main')
def run_main():
    subprocess.Popen(["python3", "main.py"])
    return "main.py executat correctament"

app.run(host='0.0.0.0', port=8080)
