import os
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_summary(data):
    today = datetime.now().strftime("%d %B %Y")

    prompt = f"""
You are an AI Managing Director analyzing a company dashboard.

DATE: {today}

DATA:
{data}

Generate a structured summary:

# 📊 MD Dashboard Summary – {today}

## 1️⃣ Admin Dashboard
⚠️ Drawbacks:
💡 Improvements:

---

## 2️⃣ Schedule Hub
⚠️ Drawbacks:
💡 Improvements:

---

## 3️⃣ Task Management (MAIN SECTION)

Analyze:
- Pending vs Completed
- In Progress workload

⚠️ Drawbacks:
💡 Improvements:

---

## 4️⃣ Reports
⚠️ Drawbacks:
💡 Improvements:

---

## 5️⃣ Projects

Includes:
- TRL progression (1–9 stages)
- Project overview (total, live, completed, on hold)
- Filters (all, planning, active, completed, on hold)

ANALYZE:
- If many projects in TRL 1–3 → early-stage heavy
- If TRL 6–9 low → poor completion
- If on_hold high → delays
- If completed low → inefficiency

⚠️ Drawbacks:
💡 Improvements:

---

## 6️⃣ Project Insights
⚠️ Drawbacks:
💡 Improvements:

---

## 7️⃣ Messaging System
⚠️ Drawbacks:
💡 Improvements:

---

## 8️⃣ Leave Management
⚠️ Drawbacks:
💡 Improvements:

---

## 9️⃣ NHRDI Analytics
⚠️ Drawbacks:
💡 Improvements:

---

## 🔥 Final Status

Rules:
- Use numbers for task + project analysis
- Be realistic and professional
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ AI Error: {str(e)}"