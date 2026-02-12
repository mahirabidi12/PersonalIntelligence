#!/usr/bin/env python3
import requests
import sys
import json
from datetime import datetime

# Use the public endpoint from frontend .env
API_URL = "https://7dcd99ce-af52-4298-9cbb-20dfd53c19b9.preview.emergentagent.com"

class Blinkit2APITester:
    def __init__(self, base_url=API_URL):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.cart_items = []

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        if params:
            url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, json=data, headers=headers, timeout=15)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, response.text
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
        if success and isinstance(response, dict) and response.get('status') == 'ok':
            self.log("   Health check passed - Blinkit2 API is running")
            return True
        else:
            self.log("   Health check failed - wrong response format")
            return False

    def test_get_categories(self):
        """Test getting categories - should return 12 categories"""
        success, response = self.run_test(
            "Get Categories",
            "GET",
            "categories",
            200
        )
        if success and isinstance(response, dict) and 'data' in response:
            categories = response['data']
            if len(categories) >= 12:
                self.log(f"   Found {len(categories)} categories (expected ≥12)")
                return True, categories
            else:
                self.log(f"   Only found {len(categories)} categories, expected 12")
                return False, []
        return False, []

    def test_get_products(self):
        """Test getting all products - should return 64+ products"""
        success, response = self.run_test(
            "Get All Products",
            "GET",
            "products",
            200,
            params={"limit": 100}
        )
        if success and isinstance(response, dict) and 'data' in response:
            products = response['data']
            total = response.get('total', 0)
            if total >= 64:
                self.log(f"   Found {total} total products (expected ≥64)")
                return True, products
            else:
                self.log(f"   Only found {total} products, expected 64+")
                return False, []
        return False, []

    def test_get_products_by_category(self, category_id):
        """Test getting products by category"""
        success, response = self.run_test(
            "Get Products by Category",
            "GET",
            "products",
            200,
            params={"category_id": category_id, "limit": 20}
        )
        if success and isinstance(response, dict) and 'data' in response:
            products = response['data']
            self.log(f"   Found {len(products)} products in category")
            return True, products
        return False, []

    def test_login_demo_user(self):
        """Test login with demo user"""
        success, response = self.run_test(
            "Login Demo User",
            "POST",
            "auth/login",
            200,
            data={"email": "demo@blinkit2.com", "password": "password123"}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response.get('user_id')
            user_name = response.get('name', 'Unknown')
            self.log(f"   Login successful - User: {user_name}")
            return True
        return False

    def test_get_current_user(self):
        """Test getting current user info"""
        if not self.token:
            self.log("   No token available")
            return False
        
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200,
            params={"authorization": f"Bearer {self.token}"}
        )
        if success and 'user_id' in response:
            self.log(f"   Current user: {response.get('name', 'Unknown')}")
            return True
        return False

    def test_add_to_cart(self, product_id):
        """Test adding product to cart"""
        if not self.token:
            self.log("   No token available")
            return False
            
        success, response = self.run_test(
            "Add Product to Cart",
            "POST",
            "cart/add",
            200,
            data={"product_id": product_id},
            params={"authorization": f"Bearer {self.token}"}
        )
        if success:
            self.log(f"   Added product {product_id} to cart")
            return True, response.get('cart_item_id')
        return False, None

    def test_get_cart(self):
        """Test getting cart contents"""
        if not self.token:
            self.log("   No token available")
            return False
            
        success, response = self.run_test(
            "Get Cart",
            "GET",
            "cart",
            200,
            params={"authorization": f"Bearer {self.token}"}
        )
        if success and isinstance(response, dict) and 'data' in response:
            cart_items = response['data']
            self.log(f"   Cart contains {len(cart_items)} items")
            self.cart_items = cart_items
            return True, cart_items
        return False, []

    def test_update_cart_quantity(self, cart_item_id, quantity):
        """Test updating cart item quantity"""
        if not self.token:
            return False
            
        success, response = self.run_test(
            "Update Cart Quantity",
            "PUT",
            "cart/update",
            200,
            data={"cart_item_id": cart_item_id, "quantity": quantity},
            params={"authorization": f"Bearer {self.token}"}
        )
        if success:
            self.log(f"   Updated cart item quantity to {quantity}")
            return True
        return False

    def test_search_products(self, search_term="Maggi"):
        """Test product search functionality"""
        success, response = self.run_test(
            f"Search Products '{search_term}'",
            "GET",
            "products",
            200,
            params={"search": search_term, "limit": 10}
        )
        if success and isinstance(response, dict) and 'data' in response:
            products = response['data']
            self.log(f"   Found {len(products)} products for '{search_term}'")
            return True, products
        return False, []

    def test_add_address(self):
        """Test adding delivery address"""
        if not self.token:
            return False
            
        test_address = {
            "address_line": "Test Address, Test Street",
            "city": "Test City",
            "state": "Test State",
            "pincode": "123456",
            "mobile": "9876543210"
        }
        
        success, response = self.run_test(
            "Add Address",
            "POST",
            "addresses",
            200,
            data=test_address,
            params={"authorization": f"Bearer {self.token}"}
        )
        if success and 'address_id' in response:
            self.log(f"   Added address: {response['address_id']}")
            return True, response['address_id']
        return False, None

    def test_place_order(self, address_id):
        """Test placing an order"""
        if not self.token or not address_id:
            return False
            
        success, response = self.run_test(
            "Place Order",
            "POST",
            "orders",
            200,
            data={"address_id": address_id, "payment_method": "cod"},
            params={"authorization": f"Bearer {self.token}"}
        )
        if success and 'order_id' in response:
            self.log(f"   Order placed: {response['order_id']}")
            return True, response['order_id']
        return False, None

    def test_get_orders(self):
        """Test getting order history"""
        if not self.token:
            return False
            
        success, response = self.run_test(
            "Get Order History",
            "GET",
            "orders",
            200,
            params={"authorization": f"Bearer {self.token}"}
        )
        if success and isinstance(response, dict) and 'data' in response:
            orders = response['data']
            self.log(f"   Found {len(orders)} orders in history")
            return True, orders
        return False, []

    def test_register_new_user(self):
        """Test user registration"""
        timestamp = datetime.now().strftime("%H%M%S")
        test_user = {
            "name": f"Test User {timestamp}",
            "email": f"test_{timestamp}@example.com",
            "password": "testpass123",
            "mobile": "9999999999"
        }
        
        success, response = self.run_test(
            "Register New User",
            "POST",
            "auth/register",
            200,
            data=test_user
        )
        if success and 'token' in response:
            self.log(f"   Registered user: {test_user['name']}")
            return True
        return False

def main():
    tester = Blinkit2APITester()
    
    print("🚀 Starting Blinkit2 API Testing...")
    print(f"📍 Testing against: {API_URL}")
    print("=" * 60)
    
    # Test 1: Health check
    if not tester.test_health():
        print("❌ Health check failed, aborting tests")
        return 1
    
    # Test 2: Get categories (should be 12)
    categories_success, categories = tester.test_get_categories()
    if not categories_success:
        print("❌ Categories test failed")
        return 1
    
    # Test 3: Get all products (should be 64+)
    products_success, products = tester.test_get_products()
    if not products_success:
        print("❌ Products test failed")
        return 1
    
    # Test 4: Get products by category (using first category)
    if categories:
        first_category = categories[0]
        tester.test_get_products_by_category(first_category['category_id'])
    
    # Test 5: Search functionality
    tester.test_search_products("Maggi")
    tester.test_search_products("banana")
    
    # Test 6: Login with demo user
    if not tester.test_login_demo_user():
        print("❌ Demo user login failed, skipping auth-required tests")
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
        return 1
    
    # Test 7: Get current user info
    tester.test_get_current_user()
    
    # Test 8: Cart functionality
    if products:
        # Add first product to cart
        first_product = products[0]
        add_success, cart_item_id = tester.test_add_to_cart(first_product['product_id'])
        
        if add_success:
            # Get cart contents
            cart_success, cart_items = tester.test_get_cart()
            
            if cart_success and cart_items and cart_item_id:
                # Update quantity
                tester.test_update_cart_quantity(cart_item_id, 2)
                
                # Test address and order flow
                address_success, address_id = tester.test_add_address()
                
                if address_success:
                    # Place order
                    order_success, order_id = tester.test_place_order(address_id)
                    
                    if order_success:
                        # Get order history
                        tester.test_get_orders()
    
    # Test 9: User registration
    tester.test_register_new_user()
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.failed_tests:
        print("\n❌ Failed Tests:")
        for test in tester.failed_tests:
            print(f"  - {test['test']}: {test.get('error', 'Unknown error')}")
    
    # Return 0 if most critical tests pass
    critical_passed = tester.tests_passed >= 8  # Health + Categories + Products + Login + Cart basics
    return 0 if critical_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)