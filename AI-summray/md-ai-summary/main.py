from services.fetch_data import fetch_data
from services.process_data import process_data
from intern_agents import generate_summary   # ✅ FIXED IMPORT
import os

# 🔹 Ensure storage folder exists
os.makedirs("storage", exist_ok=True)

# 🔹 Toggle dummy mode (recommended True if API not working)
USE_DUMMY = True


# 🔹 Save summary
def save_summary(summary):
    with open("storage/intern_summary.md", "w", encoding="utf-8") as f:
        f.write(summary)


# 🔹 Full pipeline
def run():
    try:
        print("🔄 Fetching data...")

        if USE_DUMMY:
            print("⚡ Using dummy data (Intern Mode)")

            raw = {
                "tasks_created": [
                    {"status": "completed"},
                    {"status": "completed"},
                    {"status": "inprogress"},
                    {"status": "pending"},
                    {"status": "completed"},
                    {"status": "inprogress"}
                ],
                "tasks_assigned": [
                    {"status": "pending"},
                    {"status": "inprogress"},
                    {"status": "completed"}
                ]
            }
        else:
            raw = fetch_data()

        print("\n🔍 RAW DATA:\n", raw)

        if not raw:
            print("❌ No data fetched. Stopping...")
            return

        print("🧠 Processing data...")
        processed = process_data(raw)

        print("🤖 Generating AI response...")
        summary = generate_summary(processed)

        print("\n🤖 ===== INTERN AI OUTPUT =====\n")
        print(summary)
        print("\n===============================\n")

        print("💾 Saving summary...")
        save_summary(summary)

        print("✅ Intern summary saved successfully\n")

    except Exception as e:
        print("❌ Error:", str(e))


# 🔹 Run
if __name__ == "__main__":
    run()