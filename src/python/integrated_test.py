from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class AsyncWebCrawler:
    def __init__(self):
        self.driver = None
        self.setup_browser()

    def setup_browser(self):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=9222')

            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            print("WebDriver initialized successfully.")
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            self.driver = None

    def crawl(self, start_url):
        if self.driver is None:
            print("WebDriver not initialized. Exiting crawl.")
            return
        print(f"Starting crawl on {start_url}")
        self.driver.get(start_url)
        print(f"Page title: {self.driver.title}")

    def close(self):
        if self.driver:
            self.driver.quit()
            print("WebDriver closed successfully.")
        else:
            print("WebDriver was not initialized, nothing to quit.")

def main():
    crawler = AsyncWebCrawler()
    start_url = "https://www.example.com"
    crawler.crawl(start_url)
    crawler.close()

if __name__ == "__main__":
    main() 