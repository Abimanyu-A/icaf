from selenium import webdriver
from selenium.webdriver.firefox.options import Options


class BrowserManager:

    def __init__(self):

        options = Options()
        options.accept_insecure_certs = True

        self.driver = webdriver.Firefox(options=options)

    def open(self, url):

        self.driver.get(url)

    def close(self):

        self.driver.quit()