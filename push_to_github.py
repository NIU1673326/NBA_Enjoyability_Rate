import os
import subprocess

# Configura el repositori
GITHUB_USER = "NIU1673326"  # Canvia si cal
REPO_NAME = "NBA_Enjoyability_Rate"
BRANCH = "main"
GH_TOKEN = os.environ["GH_TOKEN"]

REPO_URL = f"https://{GH_TOKEN}@github.com/{GITHUB_USER}/{REPO_NAME}.git"

# Inicialitza git si cal
if not os.path.exists(".git"):
    subprocess.run(["git", "init"])
    subprocess.run(["git", "remote", "add", "origin", REPO_URL])
    subprocess.run(["git", "checkout", "-b", BRANCH])

# Configura l'usuari si no està fet
subprocess.run(["git", "config", "--global", "user.email", "replit@auto.com"])
subprocess.run(["git", "config", "--global", "user.name", "Replit Auto"])

subprocess.run(["git", "pull", "--rebase", "origin", BRANCH])

# Fes commit i push
subprocess.run(["git", "add", "."])
subprocess.run(["git", "commit", "-m", "Actualització automàtica", "--allow-empty"])
subprocess.run(["git", "push", "origin", BRANCH])
