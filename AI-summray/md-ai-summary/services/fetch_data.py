import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL") or "https://employeemanagementsystem-production-b178.up.railway.app"
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

print("✅ USING BASE_URL:", BASE_URL)


# 🔐 LOGIN (API LOGIN)
def login():
    session = requests.Session()
    login_url = f"{BASE_URL}/accounts/login/"

    payload = {
        "username": USERNAME,
        "password": PASSWORD
    }

    try:
        res = session.post(login_url, json=payload)

        print("🔐 Login Status:", res.status_code)
        print("🔐 Response:", res.text)

        if res.status_code == 200:
            print("✅ Login successful")
            return session
        else:
            print("❌ Login failed")
            return None

    except Exception as e:
        print("❌ Login Exception:", str(e))
        return None


# 🔒 SAFE GET
def safe_get(session, endpoint):
    url = f"{BASE_URL}{endpoint}"

    try:
        res = session.get(url)

        print(f"\n🔍 API CALL → {url}")
        print("Status:", res.status_code)

        if res.status_code != 200:
            print("⚠️ API failed")
            return []

        return res.json()

    except Exception as e:
        print(f"❌ Error at {url}:", str(e))
        return []


# 📡 FETCH ONLY INTERN TASK DATA
def fetch_data():
    session = login()

    if not session:
        print("❌ Login failed. Cannot fetch data.")
        return {}

    print("\n📡 Fetching INTERN task data...")

    data = {
        "tasks_created": safe_get(session, "/tasks/viewTasks/"),
        "tasks_assigned": safe_get(session, "/tasks/viewAssignedTasks/")
    }

    print("\n✅ Task data fetched\n")
    return data