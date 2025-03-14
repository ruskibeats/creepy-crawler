from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def test_webdriver():
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--no-sandbox')  # Bypass OS security model
        options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
        options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
        options.add_argument('--remote-debugging-port=9222')  # Enable remote debugging

        # Initialize the WebDriver using Service
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        print("WebDriver initialized successfully.")

        # Test loading a simple webpage
        test_url = "https://www.example.com"
        driver.get(test_url)
        print(f"Page title: {driver.title}")

        driver.quit()
        print("WebDriver closed successfully.")
    except Exception as e:
        print(f"Error during WebDriver operation: {e}")

if __name__ == "__main__":
    test_webdriver() 