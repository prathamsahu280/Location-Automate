import asyncio
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

class AsyncMessageSender:
    def __init__(self, conversation_url):
        self.conversation_url = conversation_url
        self.driver = None
        self.queue = asyncio.Queue()
        self.processing = set()

    async def setup_driver(self):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("user-data-dir=./chrome_profile")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            await asyncio.to_thread(self.driver.get, self.conversation_url)
            await asyncio.to_thread(
                WebDriverWait(self.driver, 20).until,
                EC.presence_of_element_located((By.CLASS_NAME, "text-msg-container"))
            )
        except Exception as e:
            print(f"Error setting up the driver: {e}")
            raise

    async def send_message(self, phone_number):
        try:
            input_area = await asyncio.to_thread(
                WebDriverWait(self.driver, 20).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder='Text message']"))
            )
            await asyncio.to_thread(input_area.clear)
            await asyncio.to_thread(input_area.send_keys, phone_number)
            await asyncio.to_thread(input_area.send_keys, Keys.RETURN)
            print(f"Message sent: {phone_number}")
            self.processing.add(phone_number)
        except Exception as e:
            print(f"An error occurred while sending the message: {str(e)}")

    async def check_for_replies(self):
        while True:
            try:
                message_elements = await asyncio.to_thread(
                    self.driver.find_elements, By.CSS_SELECTOR, "mws-message-part-content"
                )
                for element in message_elements:
                    class_attribute = await asyncio.to_thread(element.get_attribute, "class")
                    if "incoming" in class_attribute:
                        message_content = await asyncio.to_thread(
                            element.find_element, By.CSS_SELECTOR, ".text-msg-content .ng-star-inserted"
                        )
                        message_text = await asyncio.to_thread(lambda: message_content.text)
                        
                        # Extract MSISDN from the reply
                        msisdn_match = re.search(r'MSISDN (\d+)', message_text)
                        if msisdn_match:
                            msisdn = msisdn_match.group(1)
                            if msisdn in self.processing:
                                print(f"Reply received for {msisdn}:")
                                print(message_text)
                                print("---")
                                self.processing.remove(msisdn)
                
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                print(f"An error occurred while checking for replies: {str(e)}")
                await asyncio.sleep(1)

    async def process_queue(self):
        while True:
            try:
                phone_number = await self.queue.get()
                await self.send_message(phone_number)
                self.queue.task_done()
            except Exception as e:
                print(f"Error processing queue: {str(e)}")
                self.queue.task_done()

    async def run(self):
        try:
            await self.setup_driver()
            check_replies_task = asyncio.create_task(self.check_for_replies())
            process_queue_task = asyncio.create_task(self.process_queue())

            while True:
                phone_number = await asyncio.to_thread(input, "Enter a phone number (or 'q' to quit): ")
                if phone_number.lower() == 'q':
                    break
                await self.queue.put(phone_number)

            await self.queue.join()
            check_replies_task.cancel()
            process_queue_task.cancel()
            await asyncio.gather(check_replies_task, process_queue_task, return_exceptions=True)
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
        finally:
            if self.driver:
                await asyncio.to_thread(self.driver.quit)

async def main():
    conversation_url = "https://messages.google.com/web/conversations/213"
    sender = AsyncMessageSender(conversation_url)
    await sender.run()

if __name__ == "__main__":
    asyncio.run(main())