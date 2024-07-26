import asyncio
import re
from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import requests
import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Set up Google Sheets credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = {
    "type": os.getenv("GOOGLE_SERVICE_ACCOUNT_TYPE"),
    "project_id": os.getenv("GOOGLE_PROJECT_ID"),
    "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GOOGLE_PRIVATE_KEY").replace('\\n', '\n') if os.getenv("GOOGLE_PRIVATE_KEY") else None,
    "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
    "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
    "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL")
}

creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scope)
google_client = gspread.authorize(creds)

class AsyncMessageSender:
    def __init__(self, conversation_url):
        self.conversation_url = conversation_url
        self.driver = None
        self.processing = {}

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

    async def send_message(self, phone_number, operator, author, ask_time):
        try:
            input_area = await asyncio.to_thread(
                WebDriverWait(self.driver, 20).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder='Text message']"))
            )
            await asyncio.to_thread(input_area.clear)
            await asyncio.to_thread(input_area.send_keys, f"{phone_number} - {operator}")
            await asyncio.to_thread(input_area.send_keys, Keys.RETURN)
            
            send_time = datetime.now()
            print(f"Message sent: {phone_number}")
            self.processing[phone_number] = send_time

            # Write to Google Sheets
            await self.write_to_sheet(phone_number, operator, author, ask_time, send_time)

            return "success"
        except Exception as e:
            print(f"An error occurred while sending the message: {str(e)}")
            return "error"

    async def write_to_sheet(self, phone_number, operator, author, ask_time, send_time):
        try:
            sheet = google_client.open_by_key('1nyxA0-gjOV3l1dCWrNm74XnXts-nxrh8k1NviGO-S6o').worksheet('Sheet1')
            values = [phone_number, operator, author, ask_time, send_time.strftime("%Y-%m-%d %H:%M:%S")]
            await asyncio.to_thread(sheet.append_row, values)
            print("Row added successfully to the spreadsheet!")
        except Exception as e:
            print(f"Error writing to spreadsheet: {str(e)}")

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
                        
                        timestamp_element = await asyncio.to_thread(
                            element.find_element, By.XPATH, "./ancestor::mws-text-message-part"
                        )
                        timestamp_str = await asyncio.to_thread(timestamp_element.get_attribute, "aria-label")
                        
                        # Extract datetime from the timestamp string
                        timestamp_match = re.search(r'Received on (.+) at (.+)\.', timestamp_str)
                        if timestamp_match:
                            date_str, time_str = timestamp_match.groups()
                            message_timestamp = datetime.strptime(f"{date_str} {time_str}", "%B %d, %Y %I:%M %p")
                        
                            msisdn_match = re.search(r'MSISDN (\d+)', message_text)
                            if msisdn_match:
                                msisdn = msisdn_match.group(1)
                                if msisdn in self.processing:
                                    sent_timestamp = self.processing[msisdn]
                                    
                                    # Compare timestamps up to the minute level
                                    if message_timestamp.replace(second=0, microsecond=0) >= sent_timestamp.replace(second=0, microsecond=0):
                                        print(f"Reply received for {msisdn}:")
                                        print(message_text)
                                        print(f"Timestamp: {timestamp_str}")
                                        print("---")
                                        del self.processing[msisdn]
                                        
                                        # Send reply back to Node.js server
                                        response = requests.post('http://localhost:3000/reply', json={
                                            'phone_number': msisdn,
                                            'reply': message_text
                                        })
                                        print(f"Sent reply to Node.js server: {response.status_code}")
                
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
    author = data.get('author')
    ask_time = data.get('date')

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(message_sender.send_message(phone_number, operator, author, ask_time))
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()

    return jsonify({'status': result})

async def main():
    await message_sender.setup_driver()
    asyncio.create_task(message_sender.check_for_replies())

    # Start Flask server in the same event loop
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:5001"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
