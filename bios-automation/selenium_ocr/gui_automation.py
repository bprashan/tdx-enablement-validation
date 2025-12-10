import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.download_manager import WDMDownloadManager
from webdriver_manager.core.http import HttpClient
from selenium.webdriver.common.action_chains import ActionChains
from requests import Response
import requests
import easyocr
from selenium.webdriver.common.keys import Keys
import urllib3
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
urllib3.disable_warnings()

if os.path.exists("workspace"):
    shutil.rmtree("workspace")

os.mkdir("workspace")

# Define the API endpoint
node_label = os.environ.get('tdx_node_label')
url = f"https://onecloudapi.intel.com/9d8e7555282bc3fc8c19ca90660e37a9/kvmlink/{node_label}"

class CustomHttpClient(HttpClient):
    def get(self, url, params=None) -> Response:
        proxies={'http': 'http://proxy-iind.intel.com:911',
         'https': 'http://proxy-iind.intel.com:912',
         }
        return requests.get(url, params,verify=False)

http_client = CustomHttpClient()
download_manager = WDMDownloadManager(http_client)
try:
    http = urllib3.PoolManager(
    cert_reqs='CERT_NONE',
    assert_hostname=False
    )

    # Sending a GET request and getting back response as HTTPResponse object.
    response = http.request('GET', url)
    print("Response Status:", response.status)

    # Check if the request was successful
    if response.status == 200:
        # Parse the JSON response
        data = response.json()
        print("Response Data:", data)
    else:
        print(f"Request failed with status code {response.status_code}")

    kvm_link = data["kvmlink"]

    print(f"KVM Link: {kvm_link}")

    # Set up Selenium WebDriver
    proxy = "http://proxy-iind.intel.com:912"
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument('--ignore-ssl-errors=yes')
    chrome_options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Chrome(options=chrome_options)

    # Open the KVM link in the browser
    driver.get(kvm_link)

    # Wait for the page to load
    time.sleep(30)

    # Get the handle of the current window
    main_window_handle = driver.current_window_handle

    # Get all window handles
    all_window_handles = driver.window_handles

    # Switch to the new window if there is more than one window handle
    for handle in all_window_handles:
        if handle != main_window_handle:
            driver.switch_to.window(handle)
            break

    driver.maximize_window()

    driver.execute_script("document.body.style.zoom='70%'")
    time.sleep(5)
    screenshot_path = r"workspace\sdp.png"
    driver.save_screenshot(screenshot_path)

    reader = easyocr.Reader(['en'], gpu=False, model_storage_directory="C:\\Users\\intel\\jinen\\bios_automation\\easyocr_models", download_enabled=False)
    result = reader.readtext(screenshot_path, detail = 0, paragraph=True)
    print(result)

    matching = [s for s in result if "login" in s or "Login" in s]
    if len(matching) > 0:
        print(" ####### Match Found: You are logged into SDP system ########")
    else:
        raise ValueError("You are not in SDP system login screen, exiting out.")

    button = driver.find_element(By.ID, "toolbariconsendCtrlAltDel")

    button.click()

    time.sleep(60)

    boot_main_screen = False
    start_time = time.time()
    timeout = 120
    while boot_main_screen == False or time.time() - start_time < timeout:
        boot_main_page = r"workspace\boot_main_screen.png"
        driver.save_screenshot(boot_main_page)

        reader = easyocr.Reader(['en'], gpu=False, model_storage_directory="C:\\Users\\intel\\jinen\\bios_automation\\easyocr_models", download_enabled=False)
        result = reader.readtext(boot_main_page, detail = 0, paragraph=True)
        print(result)

        matching = [s for s in result if "QCT" in s or "F2" in s or "QCt" in s]
        if len(matching) > 0:
            print(" ####### Match Found: You are in Boot main page ########")
            print(matching)
            actions = ActionChains(driver)
            actions.send_keys(Keys.F2)
            actions.perform()
            boot_main_screen = True

    if boot_main_screen == False:
        # Raise an exception if the condition is not met within the timeout
        raise TimeoutError("The system didn't boot up within the specified timeout")

    boot_second_screen = False
    already_in_bios_page = False
    while boot_second_screen == False:
        boot_second_page = r"workspace\boot_second_screen.png"
        driver.save_screenshot(boot_second_page)

        reader = easyocr.Reader(['en'], gpu=False, model_storage_directory="C:\\Users\\intel\\jinen\\bios_automation\\easyocr_models", download_enabled=False)
        result = reader.readtext(boot_second_page, detail = 0, paragraph=True)
        print(result)

        matching = [s for s in result if "ami" in s or "Version" in s or "AMI" in s]
        alt_matching = [s for s in result if "Vendor" in s or "Platform" in s or "Version" in s]
        if len(matching) > 0:
            print(" ####### Match Found: You are in Boot second page ########")
            print(matching)
            actions = ActionChains(driver)
            actions.send_keys(Keys.F2)
            actions.perform()
            boot_second_screen = True
        elif len(alt_matching) > 0:
            boot_second_screen = True
            already_in_bios_page = True
        else:
            boot_second_screen = False
    
    time.sleep(10)
    if already_in_bios_page == False:

        bios_main_page = r"workspace\bios_main_page.png"
        driver.save_screenshot(bios_main_page)

        reader = easyocr.Reader(['en'], gpu=False, model_storage_directory="C:\\Users\\intel\\jinen\\bios_automation\\easyocr_models", download_enabled=False)
        result = reader.readtext(bios_main_page, detail = 0, paragraph=True)
        print(result)

        matching = [s for s in result if "Vendor" in s or "Platform" in s or "Version" in s]

    if len(matching) > 0 or already_in_bios_page == True:
        print(" ####### Match Found: You are in BIOS Main page ########")
        print(matching)
        actions = ActionChains(driver)
        for i in range(3):
            actions.send_keys(Keys.ARROW_RIGHT)
            actions.perform()
            time.sleep(3)
    else:
        raise ValueError("You are not in BIOS Main page, exiting out.")

    bios_socket_configuration_page = r"workspace\bios_socket_configuration_page.png"
    driver.save_screenshot(bios_socket_configuration_page)

    reader = easyocr.Reader(['en'], gpu=False, model_storage_directory="C:\\Users\\intel\\jinen\\bios_automation\\easyocr_models", download_enabled=False)
    result = reader.readtext(bios_socket_configuration_page, detail = 0, paragraph=True)
    print(result)

    matching = [s for s in result if "Memory" in s or "Configuration" in s or "Power"]
    if len(matching) > 0:
        print(" ####### Match Found: You are in Socket Configuration page ########")
        print(matching)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ARROW_DOWN)
        actions.perform()
        actions.send_keys(Keys.ENTER)
        actions.perform()
    else:
        raise ValueError("You are not in Socket Configuration page, exiting out.")
    
    time.sleep(5)

    processor_configuration_page = r"workspace\processor_configuration_page.png"
    driver.save_screenshot(processor_configuration_page)

    reader = easyocr.Reader(['en'], gpu=False, model_storage_directory="C:\\Users\\intel\\jinen\\bios_automation\\easyocr_models", download_enabled=False)
    result = reader.readtext(processor_configuration_page, detail = 0, paragraph=True)
    print(result)

    matching = [s for s in result if "Processor" in s or "Microcode" in s]
    if len(matching) > 0:
        print(" ####### Match Found: You are in Processor Configuration page ########")
        print(matching)
        for i in range(15):
            actions.send_keys(Keys.ARROW_UP)
            actions.perform()
            time.sleep(3)

        sgx_configuration_page = r"workspace\sgx_configuration_page.png"
        driver.save_screenshot(sgx_configuration_page)

        reader = easyocr.Reader(['en'], gpu=False, model_storage_directory="C:\\Users\\intel\\jinen\\bios_automation\\easyocr_models", download_enabled=False)
        result = reader.readtext(sgx_configuration_page, detail = 0, paragraph=True)
        print(result)

        matching = [s for s in result if "SGX" in s]
        if len(matching) > 0:
            print(" ####### Match Found: You are in SGX Configuration page ########")
            actions.send_keys(Keys.ENTER)
            actions.perform()
            time.sleep(3)
            actions.send_keys(Keys.ARROW_DOWN)
            actions.perform()
            time.sleep(3)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            time.sleep(3)
            actions.send_keys('Y')
            time.sleep(10)
            
            for i in range(12):
                actions.send_keys(Keys.ARROW_DOWN)
                actions.perform()
                time.sleep(5)

            actions.send_keys(Keys.ENTER)
            actions.perform()
            time.sleep(5)

            actions.send_keys(Keys.ARROW_DOWN)
            actions.perform()
            time.sleep(5)

            final_configuration_page = r"workspace\final_configuration_page.png"
            driver.save_screenshot(final_configuration_page)

            reader = easyocr.Reader(['en'], gpu=False, model_storage_directory="C:\\Users\\intel\\jinen\\bios_automation\\easyocr_models", download_enabled=False)
            result = reader.readtext(final_configuration_page, detail = 0, paragraph=True)
            print(result)

            actions.send_keys(Keys.F10)
            actions.perform()
            time.sleep(3)

            actions.send_keys(Keys.ENTER)
            actions.perform()
        else:
            raise ValueError("You are not in SGX Configuration page, exiting out.")
    else:
        raise ValueError("You are not in Processor Configuration page, exiting out.")

    time.sleep(10)

    print(" ####### SGX Factory Reset Done ########")

    # Close the browser
    driver.quit()

except ValueError as e:
    print("Caught an exception", e)
    # Close the browser
    driver.quit()
    assert False, f"Exiting out"
except TimeoutError as e:
    print(f"Caught a timeout exception: {e}")
    # Close the browser
    driver.quit()
    assert False, f"Exiting out"
