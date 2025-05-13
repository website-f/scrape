from flask import Flask, render_template, redirect, request, session, url_for
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for Flask session

# Set up Selenium options for Brave (Chromium)
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in background
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")


def scrape_all_data(username, password):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    import time

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    data_row = {}  # Result to return

    try:
        # 1. LOGIN
        driver.get("https://arrahnueauction.bankrakyat.com.my/")
        login_button = driver.find_element(By.XPATH, '//a[@class="menu-link without-sub ng-star-inserted"]')
        login_button.click()
        time.sleep(2)

        username_input = driver.find_element(By.NAME, "userNameOrEmailAddress")
        password_input = driver.find_element(By.NAME, "password")
        username_input.send_keys(username)
        password_input.send_keys(password)
        login_submit = driver.find_element(By.XPATH, '//button[@type="submit"]')
        login_submit.click()
        time.sleep(3)

        # 2. CATALOG
        driver.get("https://arrahnueauction.bankrakyat.com.my/catalog")
        time.sleep(3)
        items = driver.find_elements(By.CLASS_NAME, "product-item")

        for item in items:
            try:
                desc = item.find_element(By.CLASS_NAME, "product-desc-text").text
                if "Grade: 18K" in desc or "Grade: 20K" in desc:
                    # Click into detail page
                    item.find_element(By.CLASS_NAME, "product-title").click()
                    time.sleep(3)

                    # Extract Type, Weight, Grade
                    props = driver.find_elements(By.CLASS_NAME, "d-flex")
                    type_ = weight = grade = ""
                    for p in props:
                        label = p.find_element(By.CLASS_NAME, "label").text.strip()
                        value = p.find_element(By.CLASS_NAME, "text").text.strip()
                        if "Type" in label:
                            type_ = value
                        elif "Weight" in label:
                            weight = value
                        elif "Grade" in label:
                            grade = value

                    # Extract Reserve Price
                    reserve_block = driver.find_element(By.XPATH, '//div[contains(@class, "col-12 mb-3") and .//div[text()="Reserve Price"]]')
                    reserve_price_raw = reserve_block.find_element(By.CLASS_NAME, "text").text.strip().replace("RM", "").replace(",", "")
                    reserve_price = float(reserve_price_raw)

                    # Fill in Bid input
                    bid_input = driver.find_element(By.ID, "bidPrice")
                    bid_input.clear()
                    bid_input.send_keys(str(reserve_price + 100))

                    # Click Bid button
                    bid_button = driver.find_element(By.XPATH, '//button[contains(text(), "Bid")]')
                    bid_button.click()

                    # Extract Branch
                    try:
                        branch_element = driver.find_element(By.XPATH, '//h4[contains(@class, "modal-title")]/span')
                        branch_text = branch_element.text.strip()
                        branch = branch_text.replace("Branch:", "").strip()
                    except:
                        branch = "Unknown"

                    # Save data so far
                    data_row = {
                        "type": type_,
                        "weight": weight,
                        "grade": grade,
                        "reserve_price": reserve_price + 100,
                        "branch": branch,
                    }
                    break
            except Exception as e:
                print("Skipping item due to error:", e)
                continue

        # 3. GOLD PRICE
        driver.get("https://www.mkspamp.com.my/pricing")
        time.sleep(3)
        row = driver.find_element(By.XPATH, '//tr[td[1]="3"]')
        cells = row.find_elements(By.TAG_NAME, "td")
        raw_price = cells[1].text.replace(",", "").strip()
        gold_price = float(raw_price) / 50
        data_row["gold_price_per_gram"] = gold_price

    except Exception as e:
        print("Error during scraping:", e)
    finally:
        driver.quit()

    return [data_row]  # Returning a list for compatibility with HTML table rendering



@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        
        session['logged_in'] = True
        session['username'] = username
        session['password'] = password
        
        return redirect(url_for('scraped_data'))

    return render_template('login.html')  # or whatever your login page is

       

@app.route('/scraped-data')
def scraped_data():
    if not session.get('logged_in'):
        return redirect(url_for('index'))

    username = session.get('username')
    password = session.get('password')
    data = scrape_all_data(username, password)
    return render_template('scrape.html', data=data)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

