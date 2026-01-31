import requests
import time
import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def get_session_keys():
    print("🔑 Otevírám prohlížeč (Headless Linux)...")
    options = Options()
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://www.sofascore.com")
        time.sleep(5)
        
        cookies = driver.get_cookies()
        user_agent = driver.execute_script("return navigator.userAgent;")
        driver.quit()
        
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
            
        headers = { "User-Agent": user_agent, "Referer": "https://www.sofascore.com/", "Accept": "*/*" }
        return session, headers
    except Exception as e:
        print(f"❌ Chyba Selenium: {e}")
        return None, None

def get_data():
    session, headers = get_session_keys()
    if not session: return []

    today = str(datetime.date.today())
    print(f"📡 Stahuji data pro: {today}")
    url_list = f"https://www.sofascore.com/api/v1/sport/football/scheduled-events/{today}"
    
    data_rows = []

    try:
        r = session.get(url_list, headers=headers)
        if r.status_code != 200: return []
        events = r.json().get("events", [])
    except: return []

    print(f"Zpracovávám {len(events)} zápasů...")
    for event in events:
        # POKUD CHCEŠ FILTR NA LIGY, ODKOMENTUJ TENTO ŘÁDEK:
        # if "Premier League" not in event.get("tournament", {}).get("name", ""): continue

        match_id = event["id"]
        status_code = event.get("status", {}).get("code", 0)
        
        home = event.get("homeTeam", {}).get("name", "")
        away = event.get("awayTeam", {}).get("name", "")
        score = f"{event.get('homeScore', {}).get('display', 0)}-{event.get('awayScore', {}).get('display', 0)}"
        status = event.get("status", {}).get("description", "")
        start_time = datetime.datetime.fromtimestamp(event.get("startTimestamp", 0)).strftime('%H:%M')
        tournament = event.get("tournament", {}).get("name", "")

        # Defaultní hodnoty
        xg_h, xg_a = 0, 0
        sh_h, sh_a = 0, 0
        bc_h, bc_a = 0, 0

        # Stahujeme detaily jen pro běžící nebo ukončené
        if status_code == 100 or event.get("status", {}).get("type") == "inprogress":
            try:
                r_stats = session.get(f"https://www.sofascore.com/api/v1/event/{match_id}/statistics", headers=headers)
                if r_stats.status_code == 200:
                    data = r_stats.json()
                    groups = []
                    if "statistics" in data:
                        for p in data["statistics"]:
                            if p["period"] == "ALL":
                                groups = p["groups"]
                                break
                    for g in groups:
                        for item in g["statisticsItems"]:
                            n = item["name"]
                            if n == "Expected goals": xg_h, xg_a = item["home"], item["away"]
                            elif n == "Total shots": sh_h, sh_a = item["home"], item["away"]
                            elif n == "Big chances": bc_h, bc_a = item["home"], item["away"]
                time.sleep(0.1)
            except: pass

        data_rows.append({
            "Čas": start_time,
            "Liga": tournament,
            "Stav": status,
            "Domácí": home,
            "Hosté": away,
            "Skóre": score,
            "xG Dom": xg_h,
            "xG Hos": xg_a,
            "Střely D": sh_h,
            "Střely H": sh_a,
            "Big Chances D": bc_h,
            "Big Chances H": bc_a
        })
    
    return data_rows

if __name__ == "__main__":
    data = get_data()
    if data:
        # Uložení do CSV (tabulky)
        df = pd.DataFrame(data)
        filename = "results.csv"
        df.to_csv(filename, index=False)
        print(f"✅ Data uložena do {filename}")
    else:
        print("⚠️ Žádná data.")
