import time
import datetime
import pandas as pd
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    print("🚀 Startuji Chrome (Headless)...")
    options = Options()
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def get_json_via_selenium(driver, url):
    try:
        driver.get(url)
        time.sleep(2)
        content = driver.find_element(By.TAG_NAME, "body").text
        return json.loads(content)
    except:
        return None

def get_data():
    driver = setup_driver()
    print("🌍 Jdu na SofaScore...")
    driver.get("https://www.sofascore.com")
    time.sleep(3)

    print("📡 Stahuji LIVE zápasy...")
    url_live = "https://www.sofascore.com/api/v1/sport/football/events/live"
    data = get_json_via_selenium(driver, url_live)
    events = data.get("events", []) if data else []
    
    if not events:
        print("⚠️ Žádné live zápasy.")
        driver.quit()
        return []

    print(f"✅ Nalezeno {len(events)} zápasů.")
    data_rows = []
    
    for event in events:
        match_id = event["id"]
        row = {
            "Čas": datetime.datetime.now().strftime('%H:%M'),
            "Minuta": event.get("status", {}).get("description", ""),
            "Liga": event.get("tournament", {}).get("name", ""),
            "Domácí": event.get("homeTeam", {}).get("name", ""),
            "Hosté": event.get("awayTeam", {}).get("name", ""),
            "Skóre": f"{event.get('homeScore', {}).get('current', 0)}-{event.get('awayScore', {}).get('current', 0)}",
            "xG Dom": 0, "xG Hos": 0
        }

        stats_data = get_json_via_selenium(driver, f"https://www.sofascore.com/api/v1/event/{match_id}/statistics")
        if stats_data and "statistics" in stats_data:
            for p in stats_data["statistics"]:
                if p["period"] == "ALL":
                    for group in p["groups"]:
                        for item in group["statisticsItems"]:
                            if item["name"] == "Expected goals":
                                row["xG Dom"], row["xG Hos"] = item["home"], item["away"]
        
        data_rows.append(row)
        time.sleep(0.5)

    driver.quit()
    return data_rows

if __name__ == "__main__":
    live_data = get_data()
    if live_data:
        df = pd.DataFrame(live_data)
        df.to_csv("live_results.csv", index=False)
        print("🎉 Hotovo!")
