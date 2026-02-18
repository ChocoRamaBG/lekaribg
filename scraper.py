import time
import os
import signal
import sys
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- 🛑 SAFETY FIRST: SIGNAL HANDLER ---
# Това е за случаите, когато ти писне и биеш Cancel.
def signal_handler(sig, frame):
    print("\n🛑 MAMKA MU! Спря ме по средата!")
    print("💾 Данните до момента са записани (нали ги пишем ред по ред, льольо).")
    print("👋 Чао, гащник. Shutting down driver...")
    try:
        if 'driver' in globals():
            driver.quit()
    except:
        pass
    sys.exit(0)

# Регистрираме сигналите (SIGINT = Ctrl+C, SIGTERM = Kill/Cancel от GitHub)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# --- 📁 ПЪТ КЪМ ПАПКИТЕ ---
# Йо шефе, тук слагаме всичко в "script/data" или където си искал
base_dir = os.getcwd()
output_dir = os.path.join(base_dir, "script", "data") # Слагам го в script/data, че да не мрънкаш

if not os.path.exists(output_dir):
    try:
        os.makedirs(output_dir)
    except:
        # Fallback ако нямаш права или папка script
        output_dir = os.path.join(base_dir, "data")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

print(f"📁 Папката е: {output_dir}. Let's cook.")

output_filename = os.path.join(output_dir, "lekaribg_data_v2.xlsx")
print(f"🎯 Данните отиват тук: {output_filename}")

# --- ⚙️ НАСТРОЙКИ НА БРАУЗЪРА ---
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument('--log-level=3')
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# --- 🚗 СТАРТИРАНЕ НА ДРАЙВЪРЧОВЦИ ---
print("⏳ Паля гумите на Chrome...")
try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("✅ Драйвърът зареди. Rizz level: 100.")
except Exception as e:
    print(f"💥 Мамка му човече, драйвърът гръмна: {e}")
    exit(1)

# --- 💾 ЗАПИСВАЧКАТА (ROW BY ROW) ---
def save_single_record(record):
    if not record: return
    try:
        # Brainrot fix: Excel append is slow, but safe for interrupts
        new_df = pd.DataFrame([record])
        
        if os.path.exists(output_filename):
            try:
                existing_df = pd.read_excel(output_filename)
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
            except:
                time.sleep(1) # Chill pill
                existing_df = pd.read_excel(output_filename)
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            final_df = new_df

        final_df.to_excel(output_filename, index=False)
        print(f"💾 {record.get('Име', 'N/A')} записан. ({record.get('Visits', 0)} visits)")
    except Exception as e:
        print(f"❌ Save Error: {e}")

# --- 🕵️‍♂️ PROFILE SCRAPER ---
def scrape_details_from_profile(url, basic_info):
    try:
        driver.get(url)
        # Малко brainrot чакане, да не ни усетят
        time.sleep(0.3) 
        
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except:
            return basic_info

        # Име (опресняваме го за всеки случай)
        try:
            full_name = driver.find_element(By.XPATH, "//h1//span[@itemprop='name']").text.strip()
            basic_info["Име"] = full_name
        except: pass

        # Таблица с данни - ТУК ТЪРСИМ ИМЕЙЛА
        try:
            # Търсим и специфичния клас за имейл, ако го има
            try:
                email_row = driver.find_element(By.CLASS_NAME, "rowwemail")
                email_link = email_row.find_element(By.TAG_NAME, "a")
                basic_info["Email"] = email_link.text.strip()
            except:
                pass # Ще пробваме по стария начин долу

            table = driver.find_element(By.ID, "TableCustomFieldsBig")
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                try:
                    th = row.find_element(By.TAG_NAME, "th").text.strip()
                    td_el = row.find_element(By.TAG_NAME, "td")
                    td = td_el.text.strip()
                    
                    if "Работно време" in th:
                        basic_info["Работно време"] = td
                    elif "Телефон" in th:
                        basic_info["Телефон"] = td
                    elif "Адрес" in th:
                        basic_info["Адрес"] = td
                    elif "Специалност" in th:
                        basic_info["Специалност"] = td
                    elif "Имейл" in th or "Email" in th:
                        # Ако не сме го хванали горе с класа
                        if "Email" not in basic_info:
                             basic_info["Email"] = td
                except: continue
        except: pass

        basic_info["Last Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return basic_info

    except Exception as e:
        print(f"💀 Profile Error: {e}")
        return basic_info

# --- 📜 MAIN LOOP (THE GRIND) ---
page = 1
print("🚀 Start the INFINITE grind...")

try:
    while True:
        target_url = f"https://lekaribg.net/listing-category/lekari/page/{page}/"
        print(f"\n📄 --- PAGE {page} --- (Малини и къпини, все тая)")
        driver.get(target_url)
        
        try:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".wlt_search_results"))
                )
            except:
                print("⛔ Няма контейнер с резултати. Андибул морков, май приключихме.")
                break

            items = driver.find_elements(By.CSS_SELECTOR, ".wlt_search_results .itemdata")
            
            if not items:
                print("⛔ Намерих 0 резултата. Game Over.")
                break

            print(f"🔎 На страницата има {len(items)} докторчовци.")
            
            doctors_on_page = []
            for item in items:
                try:
                    # Име и Линк
                    link_el = item.find_element(By.CSS_SELECTOR, "h4 a")
                    name = link_el.text.strip()
                    url = link_el.get_attribute("href")
                    
                    # Телефон (ако го има в листинга)
                    phone_backup = "-"
                    try:
                        phone_backup = item.find_element(By.CSS_SELECTOR, ".wlt_shortcode_phone").text.strip()
                    except: pass

                    # 🔥 NEW: NUMBER OF VISITS 🔥
                    # Търсим .wlt_shortcode_hits вътре в item-а
                    visits = "0"
                    try:
                        visits_el = item.find_element(By.CSS_SELECTOR, ".wlt_shortcode_hits")
                        visits = visits_el.text.strip()
                    except: 
                        visits = "N/A"

                    doc_data = {
                        "Име": name,
                        "URL": url,
                        "Телефон": phone_backup,
                        "Visits": visits, # Ето ти ги посещенията
                        "Email": "-"      # Ще го попълним после
                    }
                    doctors_on_page.append(doc_data)
                except: continue

            # Сега влизаме във всеки профил за детайли и имейл
            for doc in doctors_on_page:
                full_data = scrape_details_from_profile(doc['URL'], doc)
                save_single_record(full_data)

            page += 1
            
        except Exception as e:
            print(f"🤬 CRITICAL ERROR на страница {page}: {e}")
            page += 1
            if page > 1000: # Safety break
                print("💀 Hard limit reached.")
                break
            continue

except KeyboardInterrupt:
    print("\n🛑 Ръчно прекъсване! Чао!")

finally:
    try:
        driver.quit()
    except: pass
    print(f"\n🏁 Край. Файлът {output_filename} е готов (надявам се).")
