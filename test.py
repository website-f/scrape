# app.py
from flask import Flask, render_template, request, redirect, session, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Global variable to store auction data
dashboard_data = []

# Setup headless Chrome driver
def get_driver():
    options = Options()
    # options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    return driver

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        session['username'] = username
        session['password'] = password
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', data=dashboard_data)

@app.route('/logout')
def logout():
    # Clear the session to log out the user
    session.clear()
    return redirect('/')


@app.route('/start_automation', methods=['POST'])
def start_automation():
    global dashboard_data
    driver = get_driver()

    try:
        username = session['username']
        password = session['password']

        # Login
        driver.get("https://arrahnueauction.bankrakyat.com.my/account/login")
        time.sleep(2)
        driver.find_element(By.NAME, "userNameOrEmailAddress").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)

        # Catalog page
        driver.get("https://arrahnueauction.bankrakyat.com.my/catalog")
        time.sleep(5)
        
        # Re-fetch the cards
        cards = driver.find_elements(By.CLASS_NAME, "col-lg-4")
        total_cards = len(cards)

        data = []

        for index in range(total_cards):
            try:
                # Re-fetch the cards every time to avoid stale element reference
                cards = driver.find_elements(By.CLASS_NAME, "col-lg-4")
                card = cards[index]
        
                driver.execute_script("arguments[0].scrollIntoView(true);", card)
                card.click()
                time.sleep(3)
        
                # Extract data from the modal
                branch = driver.find_element(By.XPATH, "//h4[@class='modal-title']/span").text.replace("Branch:", "").strip()
                reserve_price_raw = driver.find_element(By.XPATH, "//div[contains(text(), 'Reserve Price')]/following-sibling::div").text
                product_type = driver.find_element(By.XPATH, "//div[contains(text(), 'Type:')]/following-sibling::div").text
                weight = driver.find_element(By.XPATH, "//div[contains(text(), 'Weight:')]/following-sibling::div").text
                grade = driver.find_element(By.XPATH, "//div[contains(text(), 'Grade:')]/following-sibling::div").text
        
                reserve_price = float(reserve_price_raw.replace("RM", "").replace(",", "").strip())
                eligible = grade.strip() in ["18K", "22K"]
        
                # Append the extracted data to the data list
                data.append({
                    'index': index,
                    'branch': branch,
                    'type': product_type,
                    'weight': weight,
                    'grade': grade,
                    'reserve_price': reserve_price,
                    'eligible': eligible
                })
        
                # Close the modal properly
                close_btn = driver.find_element(By.XPATH, "//div[contains(@class, 'modal-footer')]//button[contains(text(), 'Close')]")
                print(f"Clicking close button for card {index}")
                close_btn.click()
                print(f"Waiting for modal to close for card {index}")
        
                # Wait for modal to disappear
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "modal"))
                )
                time.sleep(1)
        
            except Exception as e:
                print(f"Error processing card {index}: {e}")
                continue
        
        # Save all data in the global variable
        dashboard_data = data
        driver.quit()
        return jsonify({'status': 'ok'})
    except Exception as e:
        driver.quit()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/bid/<int:index>', methods=['POST'])
def bid_item(index):
    try:
        username = session['username']
        password = session['password']
        item = dashboard_data[index]

        driver = get_driver()
        driver.get("https://arrahnueauction.bankrakyat.com.my/account/login")
        time.sleep(2)
        driver.find_element(By.NAME, "userNameOrEmailAddress").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)

        driver.get("https://arrahnueauction.bankrakyat.com.my/catalog")
        time.sleep(5)
        cards = driver.find_elements(By.CLASS_NAME, "col-lg-4")
        cards[index].click()
        time.sleep(3)

        bid_price = item['reserve_price'] + 10
        driver.find_element(By.ID, "bidPrice").clear()
        driver.find_element(By.ID, "bidPrice").send_keys(str(round(bid_price, 2)))
        driver.find_element(By.XPATH, "//button[contains(text(), 'Bid')]").click()
        time.sleep(1)
        driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm')]").click()
        driver.quit()
        return jsonify({'status': 'success'})
    except Exception as e:
        driver.quit()
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
