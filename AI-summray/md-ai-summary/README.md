# 🤖 AI Dashboard System (Intern + MD)

---

## 📌 Overview

This project generates **AI-powered summaries** for:

* 👩‍💻 Intern performance (task-based)
* 👨‍💼 MD dashboard (9-section company overview)

It converts raw data into **clear insights, drawbacks, and improvements**.

---

## 📁 Project Structure

```
md-ai-summary/
│
├── services/
│   ├── fetch_data.py        # Fetch data from backend
│   ├── process_data.py      # Process task data
│
├── intern_agents.py         # Intern AI logic
├── md_agent.py              # MD AI logic
│
├── main.py                  # Run INTERN summary
├── main_md.py               # Run MD dashboard
│
├── storage/                 # Output files (auto-created)
├── .env                     # Configuration file
```

---

## ⚙️ Setup

### Install dependencies

```bash
pip install requests python-dotenv groq
```

---

## 🔑 Environment Configuration (`.env`)

Create a `.env` file in your root folder.

---

### ✅ Required (Common)

```env
GROQ_API_KEY=your_groq_api_key_here
BASE_URL=https://employeemanagementsystem-production-b178.up.railway.app
```

---

### 👩‍💻 Intern Login (Optional)

```env
USERNAME=2074
PASSWORD=123
```

⚠️ Works only if backend API access is allowed
Otherwise use dummy mode

---

### 👨‍💼 MD Dashboard

No login required (uses structured/dummy data)

---

## ▶️ How to Run

---

### 🔹 Run Intern Summary

```bash
python main.py
```

---

### 🔹 Run MD Dashboard

```bash
python main_md.py
```

---

## 🔄 Dummy vs Real Data

---

### ✅ Default Mode (Recommended)

In `main.py`:

```python
USE_DUMMY = True
```

✔ Uses sample data
✔ Works without backend

---

### 🔴 Real Data Mode

Change:

```python
USE_DUMMY = False
```

✔ Fetches real data from backend
❗ Requires valid API credentials

---

## 📤 Output

* Printed in terminal
* Saved in:

```
storage/intern_summary.md
```

---

## 🧪 Example Commands

```bash
# Run intern dashboard
python main.py

# Run MD dashboard
python main_md.py
```

---

## ⚠️ Important Notes

* Frontend URL will NOT work for API calls
* Backend login may fail without proper access
* If login fails → use dummy mode

---

## 🚀 Quick Start

```bash
pip install requests python-dotenv groq
python main.py
```

---

## 🌟 Summary

* Intern → Task-based AI insights
* MD → 9-section dashboard analysis
* Works with both real and dummy data

---
