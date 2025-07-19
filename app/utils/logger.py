import json
import os
from datetime import datetime

LOG_FILE = "logs/log_activity.json"

def log_action(action, sp_name=None, status="success", details=""):
    print(LOG_FILE)
    print("os.getcwd():", os.getcwd())
    print("log path exists:", os.path.exists(LOG_FILE))
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "sp_name": sp_name,
            "status": status,
            "details": details
        }

        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w") as f:
                json.dump([log_entry], f, indent=4)
        else:
            with open(LOG_FILE, "r+") as f:
                data = json.load(f)
                data.append(log_entry)
                f.seek(0)
                json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error logging action: {e}")

