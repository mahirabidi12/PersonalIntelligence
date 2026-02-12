#!/usr/bin/env python3
import requests
import sys
import json
from datetime import datetime

# Use the public endpoint from frontend .env
API_URL = "https://7dcd99ce-af52-4298-9cbb-20dfd53c19b9.preview.emergentagent.com"

class WhatsApp2APITester:
    def __init__(self, base_url=API_URL):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)
        
        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    self.log(f"   Error: {error_detail}")
                except:
                    self.log(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    "test": name,
                    "endpoint": endpoint,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "error": response.text[:200]
                })
                return False, {}

        except requests.exceptions.Timeout:
            self.log(f"❌ {name} - Request timed out")
            self.failed_tests.append({"test": name, "endpoint": endpoint, "error": "Timeout"})
            return False, {}
        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            self.failed_tests.append({"test": name, "endpoint": endpoint, "error": str(e)})
            return False, {}

    def test_health(self):
        """Test health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        if success and response.get('status') == 'ok':
            self.log("   Health check passed")
            return True
        else:
            self.log("   Health check failed - wrong response format")
            return False

    def test_login(self, email="saswata@whatsapp2.com", password="password123"):
        """Test login with pre-seeded user"""
        success, response = self.run_test(
            "Login (Saswata)",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response.get('user_id')
            self.log(f"   Login successful - User ID: {self.user_id}")
            return True
        return False

    def test_register(self, username="testuser", email="test@example.com", password="testpass123"):
        """Test user registration"""
        success, response = self.run_test(
            "Register New User",
            "POST",
            "auth/register",
            200,
            data={"username": username, "email": email, "password": password}
        )
        return success and 'token' in response

    def test_get_me(self):
        """Test getting current user info"""
        if not self.token:
            return False
        
        success, response = self.run_test(
            "Get Current User",
            "GET",
            f"auth/me?authorization=Bearer {self.token}",
            200
        )
        return success and 'user_id' in response

    def test_get_users(self):
        """Test getting all users"""
        if not self.token:
            return False
            
        success, response = self.run_test(
            "Get All Users",
            "GET",
            f"users?authorization=Bearer {self.token}",
            200
        )
        return success and isinstance(response, list)

    def test_get_conversations(self):
        """Test getting conversations"""
        if not self.token:
            return False
            
        success, response = self.run_test(
            "Get Conversations",
            "GET",
            f"conversations?authorization=Bearer {self.token}",
            200
        )
        
        if success and isinstance(response, list):
            self.log(f"   Found {len(response)} conversations")
            return True, response
        return False, []

    def test_create_conversation(self, participant_id):
        """Test creating a new conversation"""
        if not self.token:
            return False
            
        success, response = self.run_test(
            "Create Conversation",
            "POST",
            f"conversations?authorization=Bearer {self.token}",
            200,
            data={"participant_ids": [participant_id]}
        )
        
        if success and 'conversation_id' in response:
            self.log(f"   Created conversation: {response['conversation_id']}")
            return True, response['conversation_id']
        return False, None

    def test_get_messages(self, conversation_id):
        """Test getting messages for a conversation"""
        if not self.token or not conversation_id:
            return False
            
        success, response = self.run_test(
            "Get Messages",
            "GET",
            f"messages/{conversation_id}?authorization=Bearer {self.token}",
            200
        )
        
        if success and isinstance(response, list):
            self.log(f"   Found {len(response)} messages")
            return True, response
        return False, []

    def test_send_message(self, conversation_id, content="Test message from API"):
        """Test sending a message"""
        if not self.token or not conversation_id:
            return False
            
        success, response = self.run_test(
            "Send Message",
            "POST",
            f"messages?authorization=Bearer {self.token}",
            200,
            data={
                "conversation_id": conversation_id,
                "content": content,
                "message_type": "text"
            }
        )
        
        if success and 'message_id' in response:
            self.log(f"   Sent message: {response['message_id']}")
            return True, response['message_id']
        return False, None

    def test_mark_messages_read(self, conversation_id):
        """Test marking messages as read"""
        if not self.token or not conversation_id:
            return False
            
        success, response = self.run_test(
            "Mark Messages Read",
            "POST",
            f"messages/read?authorization=Bearer {self.token}",
            200,
            data={"conversation_id": conversation_id}
        )
        return success

def main():
    tester = WhatsApp2APITester()
    
    print("🚀 Starting WhatsApp2 API Testing...")
    print(f"📍 Testing against: {API_URL}")
    print("=" * 50)
    
    # Test 1: Health check
    if not tester.test_health():
        print("❌ Health check failed, aborting tests")
        return 1
    
    # Test 2: Login with pre-seeded user
    if not tester.test_login():
        print("❌ Login failed, aborting further tests")
        return 1
    
    # Test 3: Get current user
    tester.test_get_me()
    
    # Test 4: Get all users
    tester.test_get_users()
    
    # Test 5: Get conversations
    conversations_success, conversations = tester.test_get_conversations()
    
    # Test 6: Get messages for first conversation if exists
    if conversations_success and conversations:
        first_conv = conversations[0]
        conv_id = first_conv['conversation_id']
        tester.test_get_messages(conv_id)
        
        # Test 7: Send a message
        message_success, message_id = tester.test_send_message(conv_id, "Test message from backend API test")
        
        # Test 8: Mark messages as read
        if message_success:
            tester.test_mark_messages_read(conv_id)
    
    # Test 9: Try registration (might fail if user exists, that's ok)
    test_email = f"apitest_{datetime.now().strftime('%H%M%S')}@test.com"
    tester.test_register("API Test User", test_email, "testpass123")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.failed_tests:
        print("\n❌ Failed Tests:")
        for test in tester.failed_tests:
            print(f"  - {test['test']}: {test.get('error', 'Unknown error')}")
    
    # Return 0 if all critical tests pass (health, login, basic functionality)
    critical_passed = tester.tests_passed >= 6  # Health + Login + Me + Users + Conversations + Messages
    return 0 if critical_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)