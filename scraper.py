import time
import os
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- 📁 ПЪТ КЪМ ПАПКИТЕ (GITHUB VERSION) ---
# В GitHub Actions няма C:\Users, затова правим папка 'data' в текущата директория
output_dir = os.path.join(os.getcwd(), "data")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print("📁 Папката 'data' е създадена. Cloud vibes only.")

output_filename = os.path.join(output_dir, "lekaribg_data.xlsx")
print(f"🎯 Данните ще се събират тук: {output_filename}")

# --- ⚙️ НАСТРОЙКИ НА БРАУЗЪРА (CI/CD MODE) ---
chrome_options = Options()
chrome_options.add_argument("--headless")  # 💀 ЗАДЪЛЖИТЕЛНО за GitHub Actions
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument('--log-level=3')
# Слагаме User-Agent да не ни усетят, че сме роботи
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# --- 🚗 СТАРТИРАНЕ НА ДРАЙВЪРЧОВЦИ ---
print("⏳ Паля гумите на Chrome (Headless)...")
try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("✅ Драйвърът зареди. Skibidi bop mm dada.")
except Exception as e:
    print(f"💥 Мамка му човече, драйвърът гръмна: {e}")
    exit(1) # Ако няма драйвър, спираме тока

# --- 💾 ЗАПИСВАЧКАТА ---
def save_single_record(record):
    if not record: return
    try:
        new_df = pd.DataFrame([record])
        
        if os.path.exists(output_filename):
            try:
                existing_df = pd.read_excel(output_filename)
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
            except:
                time.sleep(1)
                final_df = new_df 
        else:
            final_df = new_df

        final_df.to_excel(output_filename, index=False)
        print(f"💾 Доктор '{record.get('Име', 'N/A')}' е записан.")
    except Exception as e:
        print(f"❌ ERROR при запис: {e}")

# --- 🕵️‍♂️ PROFILE SCRAPER ---
def scrape_details_from_profile(url, basic_info):
    print(f"   👉 Visiting: {url}")
    try:
        driver.get(url)
        time.sleep(1) # GitHub сървърите са бързи, но нека не сме нахални
        
        # Тук може да няма body веднага, затова try-catch
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except:
            return basic_info

        # Име
        try:
            full_name = driver.find_element(By.XPATH, "//h1//span[@itemprop='name']").text.strip()
            basic_info["Име"] = full_name
        except: pass

        # Таблица с данни
        try:
            table = driver.find_element(By.ID, "TableCustomFieldsBig")
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                try:
                    th = row.find_element(By.TAG_NAME, "th").text.strip()
                    td = row.find_element(By.TAG_NAME, "td").text.strip()
                    
                    if "Работно време" in th:
                        basic_info["Работно време"] = td
                    elif "Телефон" in th:
                        basic_info["Телефон"] = td
                    elif "Адрес" in th:
                        basic_info["Адрес"] = td
                    elif "Специалност" in th:
                        basic_info["Специалност"] = td
                except: continue
        except: pass

        # Timestamp
        basic_info["Last Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return basic_info

    except Exception as e:
        print(f"💀 Грешка: {e}")
        return basic_info

# --- 📜 MAIN LOOP ---
page = 1
max_pages = 5 # ⚠️ Сложих малко страници за тест в GitHub, увеличи го после!

print("🚀 Start the grind...")

try:
    while page <= max_pages:
        target_url = f"https://lekaribg.net/listing-category/lekari/page/{page}/"
        print(f"\n📄 --- PAGE {page} ---")
        driver.get(target_url)
        
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".wlt_search_results")))
            items = driver.find_elements(By.CSS_SELECTOR, ".wlt_search_results .itemdata")
            
            if not items:
                print("⛔ Няма повече резултати.")
                break

            print(f"🔎 Намерени {len(items)} записа.")
            
            doctors_on_page = []
            for item in items:
                try:
                    link_el = item.find_element(By.CSS_SELECTOR, "h4 a")
                    name = link_el.text.strip()
                    url = link_el.get_attribute("href")
                    
                    # Backup Phone
                    phone_backup = "-"
                    try:
                        phone_backup = item.find_element(By.CSS_SELECTOR, ".wlt_shortcode_phone").text.strip()
                    except: pass

                    doc_data = {
                        "Име": name,
                        "URL": url,
                        "Телефон": phone_backup
                    }
                    doctors_on_page.append(doc_data)
                except: continue

            for doc in doctors_on_page:
                full_data = scrape_details_from_profile(doc['URL'], doc)
                save_single_record(full_data)

            page += 1
            
        except Exception as e:
            print(f"🤬 ГРЕШКА на страница {page}: {e}")
            page += 1
            continue

finally:
    try:
        driver.quit()
    except: pass
    print(f"\n🏁 Done. Check artifacts.")
