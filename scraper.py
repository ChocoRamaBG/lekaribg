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
# Това хваща Cancel бутона в GitHub Actions или Ctrl+C
def signal_handler(sig, frame):
    print("\n🛑 MAMKA MU! Спряха ме по средата!")
    print("💾 Данните до момента са записани (нали ги пишем ред по ред, льольо).")
    print("👋 Чао, гащник. Shutting down driver...")
    try:
        if 'driver' in globals():
            driver.quit()
    except:
        pass
    # Излизаме с код 0, за да не гърми целия pipeline, 
    # а стъпката "Upload Artifact" (ако е с if: always()) да си свърши работата.
    sys.exit(0)

# Регистрираме сигналите
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# --- 📁 НАСТРОЙКА НА ПАПКИТЕ ---
# Всичко отива в папка "data" в root директорията на проекта
base_dir = os.getcwd()
output_dir = os.path.join(base_dir, "data")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Важно: Името на файла трябва да е същото като в scrape.yml!
output_filename = os.path.join(output_dir, "lekaribg_data_v2.xlsx")

print(f"📁 Папката е: {output_dir}")
print(f"🎯 Файлът е: {output_filename}")

# --- ⚙️ НАСТРОЙКИ НА БРАУЗЪРА ---
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument('--log-level=3')
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# --- 🚗 СТАРТИРАНЕ ---
print("⏳ Паля гумите на Chrome...")
try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("✅ Драйвърът зареди. Rizz level: 100.")
except Exception as e:
    print(f"💥 Мамка му човече, драйвърът гръмна: {e}")
    sys.exit(1)

# --- 💾 ЗАПИСВАЧКАТА ---
def save_single_record(record):
    if not record: return
    try:
        new_df = pd.DataFrame([record])
        
        if os.path.exists(output_filename):
            try:
                # Четем стария, лепим новия
                existing_df = pd.read_excel(output_filename)
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
            except:
                # Ако файлът е заключен (рядко при headless, ама да има)
                time.sleep(1)
                existing_df = pd.read_excel(output_filename)
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            final_df = new_df

        final_df.to_excel(output_filename, index=False)
        print(f"💾 {record.get('Име', 'N/A')} записан. (Visits: {record.get('Visits', '0')})")
    except Exception as e:
        print(f"❌ Save Error: {e}")

# --- 🕵️‍♂️ PROFILE SCRAPER ---
def scrape_details_from_profile(url, basic_info):
    # print(f"👉 Visiting: {url}")
    try:
        driver.get(url)
        # Леко забавяне за brainrot purposes
        time.sleep(0.3) 
        
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except:
            return basic_info

        # 1. Име (опресняваме го за всеки случай)
        try:
            full_name = driver.find_element(By.XPATH, "//h1//span[@itemprop='name']").text.strip()
            basic_info["Име"] = full_name
        except: pass

        # 2. EMAIL Extraction (Specific HTML structure)
        # HTML структурата ти е: <tr class="odd rowwemail"><td class="val_email"><a ...>...</a></td></tr>
        found_email = False
        try:
            email_row = driver.find_element(By.CLASS_NAME, "rowwemail")
            email_link = email_row.find_element(By.TAG_NAME, "a")
            email_text = email_link.text.strip()
            if email_text:
                basic_info["Email"] = email_text
                found_email = True
        except:
            pass # Няма го този клас, продължаваме напред

        # 3. Обхождане на таблицата (за всичко останало + fallback за email)
        try:
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
                    
                    # Ако не сме намерили имейла по-горе, пробваме тук
                    elif not found_email and ("Имейл" in th or "Email" in th):
                        basic_info["Email"] = td
                        found_email = True

                except: continue
        except: pass

        basic_info["Last Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return basic_info

    except Exception as e:
        print(f"💀 Profile Error: {e}")
        return basic_info

# --- 📜 MAIN LOOP ---
page = 1
print("🚀 Start the INFINITE grind...")

try:
    while True:
        target_url = f"https://lekaribg.net/listing-category/lekari/page/{page}/"
        print(f"\n📄 --- PAGE {page} --- (Малини и къпини, все тая)")
        driver.get(target_url)
        
        try:
            # Чакаме да заредят резултатите
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
            
            # 1. Събираме инфото от Listing страницата (тук е броя посещения!)
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

                    # 🔥 VISITS Extraction 🔥
                    # В HTML-а е: <span class="wlt_shortcode_hits">1,681</span>
                    visits = "0"
                    try:
                        visits_el = item.find_element(By.CSS_SELECTOR, ".wlt_shortcode_hits")
                        visits = visits_el.text.strip().replace(",", "") # Махаме запетайките
                    except: 
                        visits = "N/A"

                    doc_data = {
                        "Име": name,
                        "URL": url,
                        "Телефон": phone_backup,
                        "Visits": visits,
                        "Email": "-" # Ще го попълним в детайлите
                    }
                    doctors_on_page.append(doc_data)
                except: continue

            # 2. Влизаме във всеки профил за Email и други детайли
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
    print(f"\n🏁 Край.")
