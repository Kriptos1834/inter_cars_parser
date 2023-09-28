import requests
import sys
import os
import platform
import zipfile
import urllib.request
import subprocess
import time


from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By as by
from src.settings import BASE_DIR


GECKODRIVER_VERISON = 'v0.32.2'


def install_geckodriver_linux(installation_dir, bit_type):
    url = f'https://github.com/mozilla/geckodriver/releases/latest/download/geckodriver-{GECKODRIVER_VERISON}-linux{bit_type}.tar.gz'
    urllib.request.urlretrieve(url, 'geckodriver.tar.gz')
    with zipfile.ZipFile('geckodriver.tar.gz', 'r') as zip_ref:
        zip_ref.extractall(installation_dir)
    subprocess.call(
        ['chmod', '+x', os.path.join(installation_dir, 'geckodriver')])


def install_geckodriver_macos(installation_dir):
    url = 'https://github.com/mozilla/geckodriver/releases/latest/download/geckodriver-{GECKODRIVER_VERISON}-macos.tar.gz'
    urllib.request.urlretrieve(url, 'geckodriver.tar.gz')
    with zipfile.ZipFile('geckodriver.tar.gz', 'r') as zip_ref:
        zip_ref.extractall(installation_dir)
    subprocess.call(
        ['chmod', '+x', os.path.join(installation_dir, 'geckodriver')])


def install_geckodriver_windows(installation_dir):
    url = 'https://github.com/mozilla/geckodriver/releases/latest/download/geckodriver-v0.32.2-win64.zip'
    urllib.request.urlretrieve(url, 'geckodriver.zip')
    with zipfile.ZipFile('geckodriver.zip', 'r') as zip_ref:
        zip_ref.extractall(installation_dir)
    subprocess.call(['setx', 'Path', f'%Path%;{installation_dir}\\geckodriver.exe'])


def install_geckodriver():
    os_type = platform.system()
    if os_type == 'Linux':
        bit_type = platform.architecture()[0]
        geckodriver_path = '/usr/local/bin/geckodriver'
        if not os.path.exists(geckodriver_path):
            print('[+] Geckodriver status: not installed')
            print(f'[+] Installing geckodriver {GECKODRIVER_VERISON}')
            install_geckodriver_linux(os.path.dirname(geckodriver_path), bit_type)
            print('[+] Installation complete')
        else:
            print('[+] Geckodriver status: installed')
    elif os_type == 'Darwin':
        geckodriver_path = '/usr/local/bin/geckodriver'
        if not os.path.exists(geckodriver_path):
            print('[+] Geckodriver status: not installed')
            print(f'[+] Installing geckodriver {GECKODRIVER_VERISON}')
            install_geckodriver_macos(os.path.dirname(geckodriver_path))
            print('[+] Installation complete')
        else:
            print('[+] Geckodriver status: installed')
    elif os_type == 'Windows':
        geckodriver_path = os.path.join(BASE_DIR, 'geckodriver.exe')
        if not os.path.exists(geckodriver_path):
            print('[+] Geckodriver status: not installed')
            print(f'[+] Installing geckodriver {GECKODRIVER_VERISON}')
            install_geckodriver_windows(os.path.dirname(geckodriver_path))
            print('[+] Installation complete')
        else:
            print('[+] Geckodriver status: installed')


def log_in(driver, username: str, password: str) -> None:
    wait = WebDriverWait(driver, 5)
    while True:
        try:
            username_input = wait.until(EC.element_to_be_clickable((by.ID, 'loginForm:username')))
            password_input = wait.until(EC.element_to_be_clickable((by.ID, 'loginForm:password')))
            submit_button = wait.until(EC.element_to_be_clickable((by.ID, 'loginForm:loginButton')))
            username_input.send_keys(username)
            password_input.send_keys(password)
            submit_button.click()
            driver.implicitly_wait(10)
            if driver.find_elements(by.ID, 'fail-message'):
                print('[!] Authorization Error: Wrong username or password')
                sys.exit('Authorization Error')
            return
        except StaleElementReferenceException:
            print('waiting')
            time.sleep(3)



def get_authorized_session(username: str | None = None, password: str | None = None) -> requests.Session:
    credentials = all((username, password))
    options = webdriver.FirefoxOptions()
    if credentials:
        options.add_argument('--headless')
    driver = webdriver.Firefox(options=options)

    try:
        driver.get('https://sso.intercars.eu/')
        if not credentials:
            print('[+] Waiting for authorization')
            WebDriverWait(driver, 300).until(EC.visibility_of_element_located((by.ID, 'leftMenuForm')))
        else:
            log_in(driver, username, password)
        driver.get('https://md.e-cat.intercars.eu/ru/vehicle/full-offer')
        WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located((by.CLASS_NAME, 'categoriestree__category')))
        print('[+] Authorization successful')
        print('[+] Preparing session')

        selenium_user_agent = driver.execute_script("return navigator.userAgent;")
        csrf_token = WebDriverWait(driver, 10).until(EC.presence_of_element_located((by.CSS_SELECTOR, 'input[name=_csrf]'))).get_attribute('value')
        driver.implicitly_wait(10)
        
        session = requests.Session()
        session.headers.update({
            'user-agent': selenium_user_agent,
            'X-CSRF-TOKEN': csrf_token
        })

        for cookie in driver.get_cookies():
            session.cookies.set(
                cookie['name'], cookie['value'], domain=cookie['domain'])
        
        return session

    except Exception as e:
        raise e
    finally:
        driver.quit()
