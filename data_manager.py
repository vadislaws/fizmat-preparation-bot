import json
import os
from datetime import datetime


def load_tasks():
    with open("data/tasks.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Новые функции 

USER_FILE = "data/users.json"

def load_users():
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(data):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_tests():
    with open("data/tests.json", "r", encoding="utf-8") as f:
        return json.load(f)
