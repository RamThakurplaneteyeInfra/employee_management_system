def process_data(data):
    try:
        # 🔹 Handle API + list formats
        tasks_created = data.get("tasks_created", [])
        if isinstance(tasks_created, dict):
            tasks_created = tasks_created.get("data", [])

        tasks_assigned = data.get("tasks_assigned", [])
        if isinstance(tasks_assigned, dict):
            tasks_assigned = tasks_assigned.get("data", [])

        # 🔹 Combine all tasks
        tasks = tasks_created + tasks_assigned

        total = len(tasks)

        # 🔥 Status classification
        completed = len([
            t for t in tasks if t.get("status") == "completed"
        ])

        inprogress = len([
            t for t in tasks if t.get("status") == "inprogress"
        ])

        pending = len([
            t for t in tasks if t.get("status") == "pending"
        ])

        # 🔹 Performance score
        completion_rate = (completed / total * 100) if total > 0 else 0

        return {
            "tasks_total": total,
            "tasks_completed": completed,
            "tasks_inprogress": inprogress,
            "tasks_pending": pending,
            "completion_rate": round(completion_rate, 2)
        }

    except Exception as e:
        print("❌ Processing Error:", str(e))
        return {}