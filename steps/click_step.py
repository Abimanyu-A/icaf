from core.step import Step
from selenium.webdriver.common.by import By


class ClickStep(Step):

    def __init__(self, selector):

        super().__init__("Click element")

        self.selector = selector

    def execute(self, context):

        element = context.browser.driver.find_element(By.NAME, self.selector)

        element.click()