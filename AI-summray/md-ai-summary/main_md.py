from md_agent import generate_summary
import os

os.makedirs("storage", exist_ok=True)


def save_summary(summary):
    with open("storage/md_summary.md", "w", encoding="utf-8") as f:
        f.write(summary)


def run():
    print("📊 Running MD Dashboard Summary...")

    raw = {
        "admin": {
            "expenses_trend": "moderate",
            "active_bills": "high",
            "vendors": "multiple"
        },

        "schedule": {
            "day": "working_day",
            "office_hours": "standard",
            "meetings": "moderate"
        },

        # ✅ TASKS (NUMERIC)
        "tasks": {
            "assigned": {
                "pending": 6,
                "in_progress": 4,
                "completed": 2
            },
            "reporting": 3
        },

        "reports": {
            "status": "active"
        },

        # ✅ PROJECTS (FLEXIBLE VALUES)
        "projects": {
            "creation": True,
            "trl": {
                "trl_1_3": 3,
                "trl_4_5": 2,
                "trl_6_7": 1,
                "trl_8_9": 0
            },
            "overview": {
                "total": 6,
                "live": 3,
                "completed": 2,
                "on_hold": 1
            },
            "filters": ["all", "planning", "active", "completed", "on_hold"]
        },

        "insights": {
            "issues": "moderate"
        },

        # ✅ MESSAGING
        "messages": {
            "search": "enabled",
            "access": "all_users",
            "communication": "active",
            "important_messages": "present"
        },

        "leave": {
            "requests": "moderate"
        },

        "nhrdi": {
            "analytics": "active"
        }
    }

    summary = generate_summary(raw)

    print("\n📊 ===== MD DASHBOARD OUTPUT =====\n")
    print(summary)
    print("\n=================================\n")

    save_summary(summary)
    print("✅ MD summary saved in storage/md_summary.md")


if __name__ == "__main__":
    run()