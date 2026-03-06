from core.step import Step
from selenium.webdriver.common.by import By


class FillInputStep(Step):

    def __init__(self, selector, value):

        super().__init__("Fill input")

        self.selector = selector
        self.value = value

    def execute(self, context):

        element = context.browser.driver.find_element(By.NAME, self.selector)

        element.clear()
        element.send_keys(self.value)