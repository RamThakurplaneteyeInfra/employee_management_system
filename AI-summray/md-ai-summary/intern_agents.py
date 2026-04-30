import os
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_summary(data):
    today = datetime.now().strftime("%d %B %Y")

    prompt = f"""
You are an AI mentor for interns.

Analyze the intern's performance data and give insights.

DATE: {today}

DATA:
- Total Tasks: {data.get("tasks_total")}
- Completed: {data.get("tasks_completed")}
- In Progress: {data.get("tasks_inprogress")}
- Pending: {data.get("tasks_pending")}
- Completion Rate: {data.get("completion_rate")}%

Your job:

📊 Intern Performance Summary

⚠️ Drawbacks:
- Identify real issues (too many pending or in-progress tasks)

💡 Suggestions:
- Practical steps to improve task completion

📈 Improvement Tips:
- Productivity tips

📊 Performance Level:
- Above 70% → Good
- 40–70% → Average
- Below 40% → Needs Improvement

FINAL LINE:
- Give 1 motivational sentence

RULES:
- Be short and clear
- Do NOT invent data
- Be supportive like a mentor
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ AI Error: {str(e)}"