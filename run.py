# Importing required modules
import logging
import os
import platform
import time

from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


# Basic configuration for logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format of log messages
)

# Loading Environment Variable
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
username = (os.getenv('NAUKRI_USERNAME') or os.getenv('USERNAME') or '').strip()
password = os.getenv('PASSWORD') or os.getenv('NAUKRI_PASSWORD')

# Creating Resume path
resume_path = os.path.abspath(os.path.join("resume", "Darshan_AI_Full Stack Developer.pdf"))

# Login URL
login_url = "https://www.naukri.com/nlogin/login"

# Constants
USERNAME_LOCATOR = "usernameField"
PASSWORD_LOCATOR = "passwordField"
LOGIN_BTN_LOCATOR = "//*[@type='submit' and normalize-space()='Login']"
SKIP_BTN_LOCATOR = "//*[text() = 'SKIP AND CONTINUE']"
LOGIN_CHECKPOINT_ID = "ff-inventory"

LOGIN_CHECKPOINT_TIMEOUT = 3
GLOBAL_WAIT = 0.5
FULLSCREEN_FLAG = False

# Locator Mapping
locator_mapping = {
    "ID": By.ID,
    "NAME": By.NAME,
    "XPATH": By.XPATH,
    "TAG": By.TAG_NAME,
    "CLASS": By.CLASS_NAME,
    "CSS": By.CSS_SELECTOR,
    "LINKTEXT": By.LINK_TEXT,
}


def is_headless_requested():
    """Return True when the script should run Chrome in headless mode."""
    value = os.getenv("RUN_HEADLESS", "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False

    # In a VM/server without a GUI, Chrome typically needs headless mode.
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    is_linux_server = platform.system() == "Linux" and not has_display
    is_windows_server = platform.system() == "Windows" and os.environ.get("SESSIONNAME") is None

    return is_linux_server or is_windows_server


def get_chrome_binary_path():
    """Find a usable Chrome/Chromium executable in server environments."""
    candidates = [
        os.getenv("GOOGLE_CHROME_BIN"),
        os.getenv("CHROME_BIN"),
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ]

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def get_driver():
    """
    Open Chrome to load Naukri.com with predefined options.
    Returns:
        WebDriver instance (driver) for interacting with the browser.
    """
    # Set Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popups")
    options.add_argument("--disable-gpu")
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    chrome_binary = get_chrome_binary_path()
    if chrome_binary:
        logging.info(f"Using Chrome binary at: {chrome_binary}")
        options.binary_location = chrome_binary

    if is_headless_requested():
        logging.info("Headless mode enabled for VM/server environment.")
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
    elif FULLSCREEN_FLAG:
        if platform.system() == "Windows":
            options.add_argument("--start-maximized")
        else:
            options.add_argument("--kiosk")

    driver_path = os.getenv("CHROMEDRIVER_PATH")

    try:
        service = ChromeService(driver_path) if driver_path else ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logging.info("ChromeDriver launched")
    except Exception as e:
        logging.error(f"Error launching Chrome: {e}")
        return None

    # Set implicit wait time
    driver.implicitly_wait(5)

    # Navigate to site
    try:
        driver.get(login_url)
        logging.info("Site loaded successfully")
    except Exception as e:
        logging.error(f"Error loading site: {e}")
        driver.quit()
        return None

    return driver


def is_element_present(driver, how, what):
    return driver.find_element(by=how, value=what) is not None


def get_element(driver, element_tag, locator="ID"):
    """
    Wait up to 15 seconds for an element to be available, then return it.
    Args:
        driver: WebDriver instance.
        element_tag: The tag or identifier of the element to find.
        locator: The method to locate the element (e.g., "ID", "XPATH").
    Returns:
        WebElement if found, otherwise None.
    """
    try:
        # Map locator string to the appropriate Selenium By object

        # Define an inner function for retrieving the element
        def _get_element():
            if is_element_present(driver, locator_mapping.get(locator), element_tag):
                return driver.find_element(locator_mapping.get(locator), element_tag)
            return None

        # Wait for up to 5 seconds for the element to be available
        element = WebDriverWait(driver, 5).until(lambda d: _get_element())

        if element:
            return element
        else:
            logging.warning(f"Element not found with {locator}: {element_tag}")
            return None

    except (TimeoutException, NoSuchElementException) as e:
        logging.warning(f"Error finding element with {locator}: {element_tag} - {e}")
    except Exception as e:
        logging.error(f"Error: {e}")

    return None


def wait_until_present(driver, element_tag, locator="ID", timeout=30):
    """
    Wait for an element to be present within the given timeout.
    Args:
        driver: WebDriver instance.
        element_tag: The tag or identifier of the element to find.
        locator: The method to locate the element (default is "ID").
        timeout: Maximum wait time in seconds (default is 30 seconds).
    Returns:
        bool: True if the element is present, False otherwise.
    """
    locator = locator.upper()
    driver.implicitly_wait(0)  # Disable implicit wait temporarily

    try:
        # Map locator string to the appropriate Selenium By object
        by_method = locator_mapping.get(locator)

        # Wait for the element to be present using WebDriverWait
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by_method, element_tag))
        )
        return True

    except TimeoutException:
        logging.warning(f"Element not found with {locator}: {element_tag} within {timeout} seconds.")
        return False
    except Exception as e:
        logging.error(f"Exception in WaitTillElementPresent: {e}")
        return False
    finally:
        driver.implicitly_wait(3)  # Restore the implicit wait to its default


def login():
    """
    Open Chrome browser and login to Naukri.com.
    Returns:
        tuple: (status, driver) where status is a boolean indicating success, and driver is the WebDriver instance.
    """
    status = False
    driver = None

    try:
        # Load the Naukri website
        driver = get_driver()
        if driver is None:
            logging.error("Failed to load the browser.")
            return status, driver

        page_title = (driver.title or "").lower()
        page_url = (driver.current_url or "").lower()

        if "naukri" not in page_title and "naukri" not in page_url:
            logging.warning(
                "Title/URL does not look like the Naukri login page yet, continuing to check for login form fields. "
                f"title={page_title!r}, url={page_url!r}"
            )
        logging.info("Website Loaded Successfully.")

        # Check and locate the login elements. Some Naukri pages may redirect or render different titles
        # in headless/server environments, but the login form still appears.
        if not is_element_present(driver, By.ID, USERNAME_LOCATOR):
            logging.error("Login elements not found. Unable to login.")
            return status, driver

        email_field = get_element(driver, USERNAME_LOCATOR, locator="ID")
        password_field = get_element(driver, PASSWORD_LOCATOR, locator="ID")
        login_button = get_element(driver, LOGIN_BTN_LOCATOR, locator="XPATH")

        # Fill in credentials and login
        email_field.clear()
        email_field.send_keys(username)
        password_field.clear()
        password_field.send_keys(password)
        login_button.send_keys(Keys.ENTER)

        # Handle optional skip button if it appears
        if wait_until_present(driver, SKIP_BTN_LOCATOR, "XPATH", GLOBAL_WAIT):
            get_element(driver, SKIP_BTN_LOCATOR, "XPATH").click()

        # Verify successful login
        if wait_until_present(driver, LOGIN_CHECKPOINT_ID, locator="ID", timeout=LOGIN_CHECKPOINT_TIMEOUT):
            logging.info("Login Successful")
            status = True
        else:
            logging.warning("Login checkpoint not found. Automation may fail")
        return status, driver
    except WebDriverException as wd_err:
        logging.error(f"WebDriver Error during login: {wd_err}")
    except NoSuchElementException as no_elem_err:
        logging.error(f"Element not found during login: {no_elem_err}")
    except Exception as e:
        logging.error(f"Unexpected error during login: {e}")


def check_last_update_status(driver, checkpoint_xpath, locator, wait_time):
    # Check if the resume upload was successful by checking the last updated date
    if wait_until_present(driver, checkpoint_xpath, locator=locator, timeout=wait_time):
        checkpoint = get_element(driver, checkpoint_xpath, locator="XPATH")
        if checkpoint:
            last_updated_date = checkpoint.text
            today_f1 = datetime.today().strftime("%b %d, %Y")
            # Handle single-digit day formatting
            today_f2 = datetime.today().strftime("%b %#d, %Y")

            if today_f1 in last_updated_date or today_f2 in last_updated_date:
                logging.info(f"Resume uploaded successfully. Profile update date: {last_updated_date}")
            else:
                logging.warning(f"Resume upload failed. Profile update date: {last_updated_date}")
        else:
            logging.warning("Unable to locate profile update date! Resume upload failed.")


def upload_resume(driver, resume_path):
    """
    Uploads the resume to Naukri.com.
    Args:
        driver: WebDriver instance.
        resume_path: Path to the resume file to be uploaded.
    """
    # Constants for locators and URLs
    ATTACH_CV_ID = "attachCV"
    CHECKPOINT_XPATH = "//*[contains(@class, 'updateOn')]"
    SAVE_BTN_XPATH = "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save')]"
    CLOSE_BTN_XPATH = "//*[contains(@class, 'crossIcon')]"
    PROFILE_URL = "https://www.naukri.com/mnjuser/profile"

    try:
        driver.get(PROFILE_URL)
        time.sleep(2)  # Let the page settle after navigation

        # Close any pop-ups if present
        if wait_until_present(driver, CLOSE_BTN_XPATH, "XPATH", 3):
            close_btn = get_element(driver, CLOSE_BTN_XPATH, locator="XPATH")
            if close_btn:
                close_btn.click()
                time.sleep(1)

        # Wait for the attach CV input field and upload the resume
        if wait_until_present(driver, ATTACH_CV_ID, locator="ID", timeout=10):
            attach_element = get_element(driver, ATTACH_CV_ID, locator="ID")
            attach_element.send_keys(resume_path)
            logging.info("Resume file path sent to upload input.")
            time.sleep(3)  # Wait for upload dialog / save button to appear
        else:
            logging.error("Attach CV input field not found on the profile page.")
            return

        # Save the uploaded resume if the save button is present
        if wait_until_present(driver, SAVE_BTN_XPATH, locator="XPATH", timeout=10):
            save_element = get_element(driver, SAVE_BTN_XPATH, locator="XPATH")
            if save_element:
                # Scroll into view and use JS click to bypass overlay/interactability issues
                driver.execute_script("arguments[0].scrollIntoView(true);", save_element)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", save_element)
                logging.info("Save button clicked.")
                time.sleep(3)  # Wait for save to complete
            else:
                logging.warning("Save button element could not be retrieved.")
        else:
            logging.warning("Save button not found after resume upload.")

        check_last_update_status(driver, CHECKPOINT_XPATH, "XPATH", 5)
    except TimeoutException:
        logging.error("Timeout while waiting for elements during resume upload.")
    except Exception as e:
        logging.error(f"Exception raised while uploading resume: {e}")


def clean_up(driver):
    """
    Safely quits the WebDriver session.
    Args:
        driver: The WebDriver instance to be closed.
    """
    try:
        # Check if the driver instance is still active before attempting to quit
        if driver:
            driver.quit()
            logging.info("WebDriver session closed successfully.")
    except Exception as e:
        logging.warning(f"Error occurred while closing the WebDriver session: {e}")


def run_automation():
    logging.info('Starting Automation...')
    driver = None
    try:
        status, driver = login()
        if status:
            if os.path.exists(resume_path):
                upload_resume(driver, resume_path)
            else:
                raise FileNotFoundError(f"Resume not found at path: {resume_path}")
    except Exception as ex:
        logging.error(f"Automation Failed with exception: {ex}")
    finally:
        clean_up(driver)


if __name__ == '__main__':
    run_automation()
