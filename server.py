from flask import Flask
from threading import Thread
import subprocess
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Servidor actiu"

def run():
    app.run(host='0.0.0.0', port=8080)

def executar_script():
    while True:
        subprocess.run(["python3", "main.py"])
        time.sleep(28800)  # cada 8 hores

t1 = Thread(target=run)
t2 = Thread(target=executar_script)

t1.start()
t2.start()
