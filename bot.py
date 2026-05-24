import os
import json
import time
import requests
import xml.etree.ElementTree as ET

# --- CONFIGURATION (Pulled securely from GitHub Secrets) ---
GREEN_API_URL = os.getenv("GREEN_API_URL")
ID_INSTANCE = os.getenv("ID_INSTANCE")
API_TOKEN = os.getenv("API_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_ID") 
DB_FILE = "sent_jobs.json"

# --- STATE MANAGEMENT (JSON Database) ---
def load_sent_jobs():
    """Loads the list of previously sent jobs."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_sent_job(jobs_list, url):
    """Saves the new URL to the JSON file."""
    jobs_list.append(url)
    with open(DB_FILE, 'w') as f:
        json.dump(jobs_list, f, indent=4)

# --- FETCHING LOGIC ---
def get_remote_ok_jobs():
    jobs = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get("https://remoteok.com/api", headers=headers)
        response.raise_for_status()
        data = response.json()
        for item in data[1:]:
            jobs.append({
                'title': item.get('position', 'Remote Role'),
                'company': item.get('company', 'Hiring Company'),
                'url': item.get('url', ''),
                'source': 'Remote OK'
            })
    except Exception as e:
        print(f"Error fetching Remote OK: {e}")
    return jobs

def get_wwr_jobs():
    jobs = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get("https://weworkremotely.com/remote-jobs.rss", headers=headers)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        for item in root.findall('./channel/item'):
            title_text = item.find('title').text
            url = item.find('link').text
            if ":" in title_text:
                company, title = title_text.split(":", 1)
            else:
                company = "Hiring Company"
                title = title_text
            jobs.append({
                'title': title.strip(),
                'company': company.strip(),
                'url': url,
                'source': 'We Work Remotely'
            })
    except Exception as e:
        print(f"Error fetching WWR: {e}")
    return jobs

# --- GREEN-API SENDING LOGIC ---
def send_greenapi_message(message):
    """Sends the formatted text to the WhatsApp group via Green-API."""
    # Construct the exact URL required by Green-API documentation
    url = f"{GREEN_API_URL}/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"
    
    payload = {
        "chatId": GROUP_CHAT_ID,
        "message": message
    }
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print("Message sent successfully!")
        else:
            print(f"Failed to send: {response.text}")
    except Exception as e:
        print(f"Error sending message: {e}")

# --- MAIN AUTOMATION FLOW ---
def main():
    print("Starting Multi-Source Job Scanner via Green-API...")
    
    # Load previously sent URLs
    sent_jobs = load_sent_jobs()
    
    all_new_jobs = get_wwr_jobs() + get_remote_ok_jobs()
    print(f"Total jobs scraped: {len(all_new_jobs)}")

    # Filter out jobs we have already sent
    unsent_jobs = [job for job in all_new_jobs if job['url'] not in sent_jobs]
    print(f"New, unsent jobs found: {len(unsent_jobs)}")

    # Process the newest jobs (capped at 10 per run to prevent spam limits)
    for job in unsent_jobs[:10]:
        whatsapp_message = f"*{job['title']}* 🚀\n_{job['company']}_ | 🌍 Remote\n📍 Source: {job['source']}\n\n*Apply here:* {job['url']}"
        
        print(f"Sending: {job['title']} at {job['company']}")
        send_greenapi_message(whatsapp_message)
        
        # Save to list immediately
        save_sent_job(sent_jobs, job['url'])
        
        # Wait 5 seconds between messages so Green-API/WhatsApp doesn't block you
        time.sleep(5)
        
    print("Scan complete.")

if __name__ == "__main__":
    main()
