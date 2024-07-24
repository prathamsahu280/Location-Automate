from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import time
import sys




def setup_driver():
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("user-data-dir=C:/Users/prath/AppData/Local/Google/Chrome/User Data/Profile 1")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Error setting up the driver: {e}")
        sys.exit(1)

def authenticate_and_retrieve_messages(driver, conversation_url):
    try:
        driver.get(conversation_url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "text-msg-container"))
        )
        message_elements = driver.find_elements(By.CSS_SELECTOR, "mws-message-part-content")
        print("Messages in the conversation:")
        for element in message_elements:
            try:
                # Check if the message is received or sent
                class_attribute = element.get_attribute("class")
                if "incoming" in class_attribute:
                    direction = "Received"
                elif "outgoing" in class_attribute:
                    direction = "Sent"
                else:
                    direction = "Unknown"
                # Find the message content
                message_content = element.find_element(By.CSS_SELECTOR, ".text-msg-content .ng-star-inserted").text
                # Find the timestamp
                timestamp_element = element.find_element(By.XPATH, "./ancestor::mws-text-message-part")
                timestamp = timestamp_element.get_attribute("aria-label")
                print(f"{direction}: {message_content}")
                print(f"Timestamp: {timestamp}")
                print("---")
            except Exception as e:
                print(f"Error processing a message: {e}")
    except Exception as e:
        print(f"An error occurred while retrieving messages: {e}")


def send_message(driver, message):
    try:
        input_area = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder='Text message']"))
        )
        input_area.clear()
        input_area.send_keys(message)
        input_area.send_keys(Keys.RETURN)
        
        print(f"Message sent: {message}")
        time.sleep(2)
    except Exception as e:
        print(f"An error occurred while sending the message: {str(e)}")

if __name__ == "__main__":
    conversation_url = "https://messages.google.com/web/conversations/618"
    try:
        driver = setup_driver()
        authenticate_and_retrieve_messages(driver, conversation_url)
        
        # Get user input for the message
        user_message = input("Enter the message you want to send: ")
        
        # Send the message
        send_message(driver, user_message)
        
        # Wait a bit to see the sent message
        time.sleep(5)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    finally:
        print("Program terminated.")
        driver.quit()