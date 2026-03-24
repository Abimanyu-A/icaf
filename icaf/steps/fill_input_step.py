"""
steps/fill_input_step.py
──────────────────────────────────────────────────────────────────────────────
Finds an input element by CSS selector and fills it with a value.

Improvements over original
───────────────────────────
• Uses CSS selector with WebDriverWait (element_to_be_clickable) instead of
  a raw find_element by name — avoids StaleElementReferenceError on slow UIs.
• Clears existing content with triple-click + Keys.CONTROL+A + Keys.DELETE
  to handle input fields that don't respond to element.clear().
• Logs the selector and a masked value (first 3 chars + ***) for passwords.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from icaf.core.step import Step
from icaf.utils.logger import logger


class FillInputStep(Step):
    """
    Fill an input field.

    Parameters
    ----------
    selector : str
        CSS selector for the input element.
    value : str
        Value to type into the field.
    timeout : int
        Seconds to wait for the element.  Default 10.
    """

    def __init__(self, selector: str, value: str, timeout: int = 10):
        super().__init__("Fill input")
        self.selector = selector
        self.value    = value
        self.timeout  = timeout

    def execute(self, context) -> None:
        driver = context.browser.driver

        # Mask value in logs (show first 3 chars max)
        masked = self.value[:3] + "***" if len(self.value) > 3 else "***"
        logger.info(
            "FillInputStep: selector='%s'  value='%s'",
            self.selector, masked,
        )

        try:
            element = WebDriverWait(driver, self.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selector))
            )
            # Robust clear: triple-click selects all, then delete
            element.click()
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.DELETE)
            element.clear()
            element.send_keys(self.value)

        except TimeoutException:
            logger.error(
                "FillInputStep: element '%s' not ready within %ds",
                self.selector, self.timeout,
            )
            raise