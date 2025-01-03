import os
import requests
import datetime
import pytz  # Make sure you import pytz to handle timezone-aware datetimes
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

# Flask app to keep Replit running
app = Flask(__name__)

@app.route("/")
def home():
    return "Database Monitor is running!"


# Load environment variables
SUPABASE_URL = "https://ptarggqzhmddqetvyqod.supabase.co/rest/v1"
API_KEY = os.getenv("SUPABASE_API_KEY")  # Supabase API Key (set this in Replit Secrets)

HEADERS = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def check_and_restart_devices():
    try:
        # Fetch all available phones
        print("Fetching all available phones...")
        phones_response = requests.get(f"{SUPABASE_URL}/phones?select=*", headers=HEADERS)
        print("Phones response status:", phones_response.status_code)
        print("Phones response text:", phones_response.text)

        if phones_response.status_code != 200:
            print("Error fetching phones:", phones_response.text)
            return

        phones = phones_response.json()
        print(f"Fetched {len(phones)} phones.")

        for phone in phones:
            phone_name = phone["phone_name"]
            print(f"Checking terminal output for phone: {phone_name}")

            # Fetch the last terminal output message for the phone
            terminal_response = requests.get(
                f"{SUPABASE_URL}/terminal_output?select=created_at&phone_name=eq.{phone_name}&order=created_at.desc&limit=1",
                headers=HEADERS
            )
            print(f"Terminal output response for {phone_name}: {terminal_response.status_code}")
            print(f"Terminal output text: {terminal_response.text}")

            if terminal_response.status_code != 200:
                print(f"Error fetching terminal output for {phone_name}:", terminal_response.text)
                continue

            terminal_data = terminal_response.json()

            if terminal_data:
                last_message_time = datetime.datetime.fromisoformat(terminal_data[0]["created_at"]).astimezone(pytz.utc)
                current_time = datetime.datetime.now(pytz.utc)  # Use timezone-aware current time
                print(f"Last message time for {phone_name}: {last_message_time}")
                print(f"Current time: {current_time}")

                # Check if the last message was over 10 minutes ago
                if (current_time - last_message_time).total_seconds() > 600:
                    print(f"No message in the last 10 minutes for {phone_name}. Restarting...")

                    # Insert a restart command into the service_controls table
                    restart_payload = {
                        "device_id": phone_name,
                        "action": "restart"
                    }
                    restart_response = requests.post(
                        f"{SUPABASE_URL}/service_controls",
                        headers=HEADERS,
                        json=restart_payload
                    )
                    print(f"Restart response for {phone_name}: {restart_response.status_code}")
                    print(f"Restart response text: {restart_response.text}")

                    if restart_response.status_code == 201:
                        print(f"Restart command issued successfully for {phone_name}")
                    else:
                        print(f"Error issuing restart command for {phone_name}:", restart_response.text)
            else:
                print(f"No terminal output found for {phone_name}")

    except Exception as e:
        print("Error in checking devices:", str(e))


if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    # Schedule the task to run every 1 minute
    scheduler.add_job(check_and_restart_devices, 'interval', minutes=1)
    scheduler.start()

    print("Server is running and monitoring devices. Press Ctrl+C to exit.")

    # Start the Flask app to keep Replit alive
    app.run(host="0.0.0.0", port=8080)
