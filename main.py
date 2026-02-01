import time
import datetime
import pandas as pd
import json
import os
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
    
    # DŮLEŽITÉ: Maskování, aby si SofaScore myslel, že jsme běžný uživatel
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def get_json_via_selenium(driver, url):
    """
    Trik: Otevřeme API URL přímo v prohlížeči.
    Chrome zobrazí JSON jako text na stránce (v tagu <body> nebo <pre>).
    My ten text vezmeme a převedeme na data.
    """
    try:
        driver.get(url)
        # Čekáme, až Cloudflare/SofaScore ochrana proběhne
        time.sleep(3) 
        
        # Vytáhneme text ze stránky
        content = driver.find_element(By.TAG_NAME, "body").text
        
        # Zkusíme to převést na JSON
        data = json.loads(content)
        return data
    except Exception as e:
        print(f"❌ Chyba při stahování {url}: {e}")
        return None

def get_data():
    driver = setup_driver()
    
    # 1. Nejprve jdeme na hlavní stránku pro cookies a validaci
    print("🌍 Jdu na hlavní stránku SofaScore...")
    driver.get("https://www.sofascore.com")
    time.sleep(5)

    # 2. Zjistíme dnešní datum
    today = str(datetime.date.today())
    print(f"📡 Stahuji rozpis pro: {today}")
    
    # 3. Stáhneme seznam zápasů PŘES PROHLÍŽEČ
    url_list = f"https://www.sofascore.com/api/v1/sport/football/scheduled-events/{today}"
    data = get_json_via_selenium(driver, url_list)
    
    events = data.get("events", []) if data else []
    
    if not events:
        print("⚠️ API nevrátilo žádné zápasy (možná blokace IP).")
        # I když nic nenajdeme, driver musíme zavřít
        driver.quit()
        return []

    print(f"✅ Nalezeno {len(events)} zápasů. Zpracovávám...")
    
    data_rows = []
    
    # Projdeme zápasy (omezíme počet pro test, aby to neběželo hodinu, nebo všechny)
    for event in events:
        # Filtr na ligy? (Pokud chceš všechny, nech zakomentované)
        # if "Premier League" not in event.get("tournament", {}).get("name", ""): continue

        match_id = event["id"]
        status_code = event.get("status", {}).get("code", 0)
        
        # Základní info
        row = {
            "Čas": datetime.datetime.fromtimestamp(event.get("startTimestamp", 0)).strftime('%H:%M'),
            "Liga": event.get("tournament", {}).get("name", ""),
            "Stav": event.get("status", {}).get("description", ""),
            "Domácí": event.get("homeTeam", {}).get("name", ""),
            "Hosté": event.get("awayTeam", {}).get("name", ""),
            "Skóre": f"{event.get('homeScore', {}).get('display', 0)}-{event.get('awayScore', {}).get('display', 0)}",
            "xG Dom": 0, "xG Hos": 0,
            "Střely D": 0, "Střely H": 0,
            "Sance D": 0, "Sance H": 0
        }

        # Stahujeme statistiky jen pro běžící (InProgress) nebo ukončené (Ended - 100)
        if status_code == 100 or event.get("status", {}).get("type") == "inprogress":
            stats_url = f"https://www.sofascore.com/api/v1/event/{match_id}/statistics"
            stats_data = get_json_via_selenium(driver, stats_url)
            
            if stats_data and "statistics" in stats_data:
                groups = []
                for p in stats_data["statistics"]:
                    if p["period"] == "ALL":
                        groups = p["groups"]
                        break
                
                for g in groups:
                    for item in g["statisticsItems"]:
                        n = item["name"]
                        if n == "Expected goals": 
                            row["xG Dom"], row["xG Hos"] = item["home"], item["away"]
                        elif n == "Total shots": 
                            row["Střely D"], row["Střely H"] = item["home"], item["away"]
                        elif n == "Big chances": 
                            row["Sance D"], row["Sance H"] = item["home"], item["away"]
            
            # Malá pauza mezi requesty
            time.sleep(1)

        data_rows.append(row)

    driver.quit()
    return data_rows

if __name__ == "__main__":
    data = get_data()
    
    # Vytvoříme CSV VŽDY, i když je prázdné (aby GitHub nehlásil chybu)
    if data:
        df = pd.DataFrame(data)
        df.to_csv("results.csv", index=False)
        print(f"🎉 Úspěch! Uloženo {len(data)} řádků do results.csv")
    else:
        print("⚠️ Žádná data, vytvářím prázdný soubor.")
        df = pd.DataFrame(columns=["Čas", "Liga", "Stav", "Domácí", "Hosté", "Skóre", "xG Dom", "xG Hos"])
        df.to_csv("results.csv", index=False)
