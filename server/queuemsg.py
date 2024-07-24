import asyncio
import re
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

app = Flask(__name__)

class AsyncMessageSender:
    def __init__(self, conversation_url):
        self.conversation_url = conversation_url
        self.driver = None
        self.processing = set()

    async def setup_driver(self):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("user-data-dir=C:/Users/prath/AppData/Local/Google/Chrome/User Data/Profile 1")
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

    async def send_message(self, phone_number, operator):
        try:
            input_area = await asyncio.to_thread(
                WebDriverWait(self.driver, 20).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder='Text message']"))
            )
            await asyncio.to_thread(input_area.clear)
            await asyncio.to_thread(input_area.send_keys, f"{phone_number} - {operator}")
            await asyncio.to_thread(input_area.send_keys, Keys.RETURN)
            print(f"Message sent: {phone_number} - {operator}")
            self.processing.add(phone_number)
            return "success"
        except Exception as e:
            print(f"An error occurred while sending the message: {str(e)}")
            return "error"

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
                        
                        msisdn_match = re.search(r'MSISDN (\d+)', message_text)
                        if msisdn_match:
                            msisdn = msisdn_match.group(1)
                            if msisdn in self.processing:
                                print(f"Reply received for {msisdn}:")
                                print(message_text)
                                print("---")
                                self.processing.remove(msisdn)
                
                await asyncio.sleep(10)
            except Exception as e:
                print(f"An error occurred while checking for replies: {str(e)}")
                await asyncio.sleep(10)

message_sender = AsyncMessageSender("https://messages.google.com/web/conversations/618")

@app.route('/send', methods=['POST'])
def send_message():
    data = request.get_json()
    phone_number = data.get('phone_number')
    operator = data.get('operator')

    # Run send_message coroutine
    result = asyncio.run(message_sender.send_message(phone_number, operator))
    return jsonify({'status': result})

async def main():
    await message_sender.setup_driver()
    asyncio.create_task(message_sender.check_for_replies())

    # Start Flask server in the same event loop
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:5000"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
