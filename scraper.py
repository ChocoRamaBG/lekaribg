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

# --- 📁 ПЪТ КЪМ ПАПКИТЕ (GITHUB ACTIONS MODE) ---
# В облака сме, правим папка 'data' при скрипта
output_dir = os.path.join(os.getcwd(), "data")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print("📁 Папката 'data' е готова. Let's cook.")

output_filename = os.path.join(output_dir, "lekaribg_full_data.xlsx")
print(f"🎯 Данните отиват тук: {output_filename}")

# --- ⚙️ НАСТРОЙКИ НА БРАУЗЪРА ---
chrome_options = Options()
chrome_options.add_argument("--headless")  # Без прозорец (задължително за сървъра)
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
    print("✅ Драйвърът зареди. Skibidi bop yes yes.")
except Exception as e:
    print(f"💥 Мамка му човече, драйвърът гръмна: {e}")
    exit(1)

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
                existing_df = pd.read_excel(output_filename)
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            final_df = new_df

        final_df.to_excel(output_filename, index=False)
        print(f"💾 {record.get('Име', 'N/A')} записан.")
    except Exception as e:
        print(f"❌ Save Error: {e}")

# --- 🕵️‍♂️ PROFILE SCRAPER ---
def scrape_details_from_profile(url, basic_info):
    print(f"   👉 Visiting: {url}")
    try:
        driver.get(url)
        # Намалих малко времето, за да върви по-бързо в GitHub, но не прекалено
        time.sleep(0.5) 
        
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

        basic_info["Last Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return basic_info

    except Exception as e:
        print(f"💀 Profile Error: {e}")
        return basic_info

# --- 📜 MAIN LOOP (INFINITE GRIND) ---
page = 1
# ВНИМАНИЕ: Махнахме max_pages. Цикълът е безкраен, докато не спре да намира резултати.

print("🚀 Start the INFINITE grind...")

try:
    while True:
        target_url = f"https://lekaribg.net/listing-category/lekari/page/{page}/"
        print(f"\n📄 --- PAGE {page} ---")
        driver.get(target_url)
        
        try:
            # Чакаме за резултати или съобщение за грешка
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".wlt_search_results"))
                )
            except:
                # Ако няма контейнер с резултати след 5 секунди, значи сме стигнали края
                print("⛔ Няма контейнер с резултати. Вероятно край на страниците.")
                break

            items = driver.find_elements(By.CSS_SELECTOR, ".wlt_search_results .itemdata")
            
            # ВТОРА ПРОВЕРКА: Ако контейнерът го има, но е празен
            if not items:
                print("⛔ Намерих 0 резултата. Game Over. Финито.")
                break

            print(f"🔎 На страницата има {len(items)} доктори.")
            
            doctors_on_page = []
            for item in items:
                try:
                    link_el = item.find_element(By.CSS_SELECTOR, "h4 a")
                    name = link_el.text.strip()
                    url = link_el.get_attribute("href")
                    
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

            # Обработка на списъка
            for doc in doctors_on_page:
                full_data = scrape_details_from_profile(doc['URL'], doc)
                save_single_record(full_data)

            page += 1
            
        except Exception as e:
            print(f"🤬 CRITICAL ERROR на страница {page}: {e}")
            # Ако гръмне страницата, пробваме следващата за всеки случай, или спираме
            # За да сме сигурни, че няма да зацикли, увеличаваме брояча
            page += 1
            if page > 500: # Hard limit, да не гръмне сървъра на GitHub ако нещо се обърка брутално
                print("💀 Hard limit reached (500 pages). Stopping safety protocol.")
                break
            continue

finally:
    try:
        driver.quit()
    except: pass
    print(f"\n🏁 Всичко приключи. Данните са в артефактите.")
