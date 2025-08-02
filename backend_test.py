import requests
import sys
import json
from datetime import datetime

class LessonHubAPITester:
    def __init__(self, base_url="https://8bec313c-42bc-492f-8514-71511295d06c.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_id = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_class_id = None
        self.created_lesson_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if self.session_id and 'X-Session-ID' not in test_headers:
            test_headers['X-Session-ID'] = self.session_id

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Method: {method}")
        print(f"   Headers: {test_headers}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            print(f"   Response Status: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"   Response Data: {json.dumps(response_data, indent=2)}")
            except:
                print(f"   Response Text: {response.text}")
                response_data = {}

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")

            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root endpoint"""
        success, response = self.run_test(
            "Root Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_auth_me_without_session(self):
        """Test /api/auth/me without session (should fail)"""
        success, response = self.run_test(
            "Auth Me Without Session",
            "GET",
            "api/auth/me",
            401
        )
        return success

    def test_create_profile_without_session(self):
        """Test creating profile without session_id (should fail)"""
        success, response = self.run_test(
            "Create Profile Without Session",
            "POST",
            "api/auth/profile",
            400,
            data={}
        )
        return success

    def test_create_profile_with_invalid_session(self):
        """Test creating profile with invalid session_id"""
        success, response = self.run_test(
            "Create Profile With Invalid Session",
            "POST",
            "api/auth/profile",
            401,
            data={"session_id": "invalid_session_123"}
        )
        return success

    def test_classes_without_auth(self):
        """Test getting classes without authentication"""
        success, response = self.run_test(
            "Get Classes Without Auth",
            "GET",
            "api/classes",
            401
        )
        return success

    def test_lessons_without_auth(self):
        """Test getting lessons without authentication"""
        success, response = self.run_test(
            "Get Lessons Without Auth",
            "GET",
            "api/lessons",
            401
        )
        return success

    def test_messages_without_auth(self):
        """Test getting messages without authentication"""
        success, response = self.run_test(
            "Get Messages Without Auth",
            "GET",
            "api/messages",
            401
        )
        return success

    def test_notifications_without_auth(self):
        """Test getting notifications without authentication"""
        success, response = self.run_test(
            "Get Notifications Without Auth",
            "GET",
            "api/notifications",
            401
        )
        return success

    def test_google_auth_url_without_auth(self):
        """Test Google auth URL without authentication"""
        success, response = self.run_test(
            "Google Auth URL Without Auth",
            "GET",
            "api/google/auth-url",
            401
        )
        return success

    def test_google_slides_without_auth(self):
        """Test Google slides without authentication"""
        success, response = self.run_test(
            "Google Slides Without Auth",
            "GET",
            "api/google/slides",
            401
        )
        return success

    def test_google_docs_without_auth(self):
        """Test Google docs without authentication"""
        success, response = self.run_test(
            "Google Docs Without Auth",
            "GET",
            "api/google/docs",
            401
        )
        return success

    def test_create_class_without_auth(self):
        """Test creating class without authentication"""
        success, response = self.run_test(
            "Create Class Without Auth",
            "POST",
            "api/classes",
            401,
            data={"name": "Test Class", "description": "Test Description"}
        )
        return success

    def test_create_lesson_without_auth(self):
        """Test creating lesson without authentication"""
        success, response = self.run_test(
            "Create Lesson Without Auth",
            "POST",
            "api/lessons",
            401,
            data={"title": "Test Lesson", "description": "Test Description", "class_id": "test_id"}
        )
        return success

    def test_send_message_without_auth(self):
        """Test sending message without authentication"""
        success, response = self.run_test(
            "Send Message Without Auth",
            "POST",
            "api/messages",
            401,
            data={"recipient_id": "test_id", "message": "Test message"}
        )
        return success

    def print_summary(self):
        """Print test summary"""
        print(f"\n" + "="*60)
        print(f"📊 TEST SUMMARY")
        print(f"="*60)
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print(f"🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️  Some tests failed. Check the logs above for details.")
            return 1

def main():
    print("🚀 Starting LessonHub API Tests...")
    print("="*60)
    
    tester = LessonHubAPITester()
    
    # Test basic endpoints
    print("\n📋 TESTING BASIC ENDPOINTS")
    print("-" * 40)
    tester.test_root_endpoint()
    
    # Test authentication endpoints
    print("\n🔐 TESTING AUTHENTICATION ENDPOINTS")
    print("-" * 40)
    tester.test_auth_me_without_session()
    tester.test_create_profile_without_session()
    tester.test_create_profile_with_invalid_session()
    
    # Test protected endpoints without authentication
    print("\n🛡️  TESTING PROTECTED ENDPOINTS (WITHOUT AUTH)")
    print("-" * 40)
    tester.test_classes_without_auth()
    tester.test_lessons_without_auth()
    tester.test_messages_without_auth()
    tester.test_notifications_without_auth()
    tester.test_create_class_without_auth()
    tester.test_create_lesson_without_auth()
    tester.test_send_message_without_auth()
    
    # Test Google integration endpoints without authentication
    print("\n🔗 TESTING GOOGLE INTEGRATION ENDPOINTS (WITHOUT AUTH)")
    print("-" * 40)
    tester.test_google_auth_url_without_auth()
    tester.test_google_slides_without_auth()
    tester.test_google_docs_without_auth()
    
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())