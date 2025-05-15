# app.py
from flask import Flask, render_template, request, redirect, session, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException
)
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

def close_modal(driver, index):
    try:
        # Wait for modal and close button to be visible
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.modal.show"))
        )

        # Try locating btn-close within the modal by filtering its parent container
        modal = driver.find_element(By.CSS_SELECTOR, "div.modal.show")
        close_buttons = modal.find_elements(By.CSS_SELECTOR, "button.btn-close")

        if not close_buttons:
            print(f"❌ No close button found in modal for card {index}")
            return False

        close_button = close_buttons[0]

        # Scroll it into view just in case
        driver.execute_script("arguments[0].scrollIntoView(true);", close_button)
        time.sleep(0.5)

        # Click it using JS
        driver.execute_script("arguments[0].click();", close_button)
        print(f"✅ Clicked close (btn-close) for card {index}")

        # Wait for modal to disappear
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element(modal)
        )
        return True

    except Exception as e:
        print(f"❌ Failed to close modal for card {index}: {e}")
        return False




@app.route('/start_automation', methods=['POST'])
def start_automation():
    global dashboard_data
    driver = get_driver()  # Your driver init function

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

        # Navigate to catalog page
        driver.get("https://arrahnueauction.bankrakyat.com.my/catalog")
        time.sleep(5)

        data = []

        # Get initial card count
        cards = driver.find_elements(By.CLASS_NAME, "col-lg-4")
        total_cards = len(cards)

        for index in range(total_cards):
            try:
                # Wait for modal to be closed before clicking next card
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "modal"))
                )

                # Re-fetch cards each time (DOM might have changed)
                cards = driver.find_elements(By.CLASS_NAME, "col-lg-4")
                card = cards[index]

                # Scroll card into view
                driver.execute_script("arguments[0].scrollIntoView(true);", card)

                # Retry clicking card up to 3 times if intercepted or stale
                retries = 3
                while retries > 0:
                    try:
                        card.click()
                        break
                    except (ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException) as e:
                        print(f"Retry clicking card {index} due to: {e}")
                        time.sleep(1)
                        retries -= 1
                        # Re-fetch the card element if stale
                        cards = driver.find_elements(By.CLASS_NAME, "col-lg-4")
                        card = cards[index]
                else:
                    print(f"Failed to click card {index} after retries")
                    continue

                time.sleep(3)  # Wait for modal animation

                # Extract modal data
                branch = driver.find_element(By.XPATH, "//h4[@class='modal-title']/span").text.replace("Branch:", "").strip()
                reserve_price_raw = driver.find_element(By.XPATH, "//div[contains(text(), 'Reserve Price')]/following-sibling::div").text
                current_highest_raw = driver.find_element(By.XPATH, "//div[contains(text(), 'Current highest bid')]/following-sibling::div").text
                product_type = driver.find_element(By.XPATH, "//div[contains(text(), 'Type:')]/following-sibling::div").text
                weight = driver.find_element(By.XPATH, "//div[contains(text(), 'Weight:')]/following-sibling::div").text
                grade = driver.find_element(By.XPATH, "//div[contains(text(), 'Grade:')]/following-sibling::div").text

                reserve_price = float(reserve_price_raw.replace("RM", "").replace(",", "").strip())
                eligible = grade.strip() in ["18K", "22K"]

                data.append({
                    'index': index,
                    'branch': branch,
                    'type': product_type,
                    'weight': weight,
                    'grade': grade,
                    'reserve_price': reserve_price,
                    'eligible': eligible,
                    'current_highest': current_highest_raw
                })

                # Close modal
                if not close_modal(driver, index):
                    continue




            except Exception as e:
                print(f"Error processing card {index}: {e}")
                continue

        # Save data globally or handle as needed
        dashboard_data = data

        driver.quit()
        return jsonify({'status': 'ok'})

    except Exception as e:
        driver.quit()
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/bid/<int:index>', methods=['POST'])
def bid_item(index):
    try:
        # Main account credentials
        username = session['username']
        password = session['password']
        item = dashboard_data[index]

        reserve_price_str = item['current_highest']
        reserve_price = float(reserve_price_str.replace("RM", "").replace(",", "").strip())

        # ---------- Step 1: Bid with Main Account ----------
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

        # bid_price = reserve_price + 10
        # driver.find_element(By.ID, "bidPrice").clear()
        # driver.find_element(By.ID, "bidPrice").send_keys(str(round(bid_price, 2)))
        driver.find_element(By.XPATH, "//button[contains(text(), 'Bid')]").click()
        time.sleep(1)
        driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm')]").click()
        driver.quit()

        # ---------- Step 2: Login with Second Account & Bid 5 Times ----------
        second_username = "izzat916"
        second_password = "Abcd1111"

        second_driver = get_driver()
        second_driver.get("https://arrahnueauction.bankrakyat.com.my/account/login")
        time.sleep(2)
        second_driver.find_element(By.NAME, "userNameOrEmailAddress").send_keys(second_username)
        second_driver.find_element(By.NAME, "password").send_keys(second_password)
        second_driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)

        second_driver.get("https://arrahnueauction.bankrakyat.com.my/catalog")
        time.sleep(5)
        cards = second_driver.find_elements(By.CLASS_NAME, "col-lg-4")
        cards[index].click()
        time.sleep(3)

        for i in range(5):
            bid_price += 100
            second_driver.find_element(By.ID, "bidPrice").clear()
            second_driver.find_element(By.ID, "bidPrice").send_keys(str(round(bid_price, 2)))
            second_driver.find_element(By.XPATH, "//button[contains(text(), 'Bid')]").click()
            time.sleep(1)
            second_driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm')]").click()
            time.sleep(2)

        second_driver.quit()
        return jsonify({'status': 'success'})

    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        try:
            second_driver.quit()
        except:
            pass
        return jsonify({'status': 'error', 'message': str(e)})


if __name__ == '__main__':
     app.run(debug=True, port=5050)
