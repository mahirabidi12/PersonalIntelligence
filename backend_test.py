#!/usr/bin/env python3
"""
Comprehensive Backend Testing Script for AgentV1.2
Tests both Blinkit2 API endpoints and agentV1.2 code validation
"""

import requests
import sys
import os
import subprocess
import importlib.util
from datetime import datetime
from pathlib import Path

# Get backend URL from frontend .env
BACKEND_URL = "https://chat-messenger-app-7.preview.emergentagent.com"

class BackendTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
    def log_test(self, test_name, passed, details=""):
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {test_name}")
        else:
            print(f"❌ {test_name}: {details}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        
    def test_blinkit2_health(self):
        """Test Blinkit2 health endpoint returns {status: ok, app: Blinkit2}"""
        try:
            response = requests.get(f"{BACKEND_URL}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok" and data.get("app") == "Blinkit2":
                    self.log_test("Blinkit2 /api/health returns correct format", True)
                    return True
                else:
                    self.log_test("Blinkit2 /api/health returns correct format", False, 
                                f"Expected {{status: ok, app: Blinkit2}}, got {data}")
                    return False
            else:
                self.log_test("Blinkit2 /api/health returns correct format", False, 
                            f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Blinkit2 /api/health returns correct format", False, str(e))
            return False
            
    def test_blinkit2_categories(self):
        """Test Blinkit2 categories API returns 12 categories"""
        try:
            response = requests.get(f"{BACKEND_URL}/api/categories", timeout=10)
            if response.status_code == 200:
                data = response.json()
                categories = data.get("data", [])  # Fixed: API returns "data" not "categories"
                if len(categories) == 12:
                    self.log_test("Blinkit2 /api/categories returns 12 categories", True)
                    return True
                else:
                    self.log_test("Blinkit2 /api/categories returns 12 categories", False, 
                                f"Expected 12 categories, got {len(categories)}")
                    return False
            else:
                self.log_test("Blinkit2 /api/categories returns 12 categories", False,
                            f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Blinkit2 /api/categories returns 12 categories", False, str(e))
            return False
    
    def check_file_exists(self, filepath, description):
        """Check if a file exists"""
        path = Path(filepath)
        exists = path.exists()
        self.log_test(f"{description} exists", exists, 
                     f"File not found: {filepath}" if not exists else "")
        return exists
    
    def check_python_syntax(self, filepath, description):
        """Check if a Python file has valid syntax"""
        try:
            result = subprocess.run([
                'python3', '-c', f'import ast; ast.parse(open(r"{filepath}").read())'
            ], capture_output=True, text=True, cwd='/app')
            
            if result.returncode == 0:
                self.log_test(f"{description} has valid Python syntax", True)
                return True
            else:
                self.log_test(f"{description} has valid Python syntax", False, 
                            result.stderr.strip())
                return False
        except Exception as e:
            self.log_test(f"{description} has valid Python syntax", False, str(e))
            return False
    
    def check_python_imports(self, filepath, description):
        """Check if a Python file's imports work"""
        try:
            # Change to agentV1.2 directory for imports to work
            result = subprocess.run([
                'python3', '-c', f'''
import sys
import os
sys.path.insert(0, "/app/agentV1.2")
os.chdir("/app/agentV1.2")
spec = __import__("importlib.util", fromlist=["spec_from_file_location"]).spec_from_file_location("test_module", r"{filepath}")
module = __import__("importlib.util", fromlist=["module_from_spec"]).module_from_spec(spec)
spec.loader.exec_module(module)
print("Imports successful")
'''
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.log_test(f"{description} imports work", True)
                return True
            else:
                self.log_test(f"{description} imports work", False, 
                            result.stderr.strip())
                return False
        except subprocess.TimeoutExpired:
            self.log_test(f"{description} imports work", False, "Import check timeout")
            return False
        except Exception as e:
            self.log_test(f"{description} imports work", False, str(e))
            return False
    
    def check_html_valid(self, filepath, description):
        """Basic HTML validation"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Basic checks
            has_doctype = '<!DOCTYPE html>' in content
            has_html_tags = '<html' in content and '</html>' in content
            has_head = '<head>' in content and '</head>' in content
            has_body = '<body>' in content and '</body>' in content
            
            if has_doctype and has_html_tags and has_head and has_body:
                self.log_test(f"{description} is valid HTML", True)
                return True
            else:
                missing = []
                if not has_doctype: missing.append("DOCTYPE")
                if not has_html_tags: missing.append("html tags")
                if not has_head: missing.append("head tags")
                if not has_body: missing.append("body tags")
                self.log_test(f"{description} is valid HTML", False, 
                            f"Missing: {', '.join(missing)}")
                return False
                
        except Exception as e:
            self.log_test(f"{description} is valid HTML", False, str(e))
            return False
    
    def test_agentV1_2_structure(self):
        """Test agentV1.2 folder structure and file validity"""
        base_path = "/app/agentV1.2"
        
        # Check folder exists
        self.check_file_exists(base_path, "agentV1.2 folder")
        
        # Check main Python files exist and have valid syntax
        python_files = [
            ("main.py", "agentV1.2/main.py"),
            ("config.py", "agentV1.2/config.py"),
            ("core/orchestrator.py", "agentV1.2/core/orchestrator.py"),
            ("core/memory.py", "agentV1.2/core/memory.py"), 
            ("core/intent.py", "agentV1.2/core/intent.py"),
            ("agents/whatsapp_agent.py", "agentV1.2/agents/whatsapp_agent.py"),
            ("agents/blinkit_agent.py", "agentV1.2/agents/blinkit_agent.py"),
            ("agents/browser_agent.py", "agentV1.2/agents/browser_agent.py"),
            ("events/bus.py", "agentV1.2/events/bus.py"),
        ]
        
        for file_path, description in python_files:
            full_path = f"{base_path}/{file_path}"
            if self.check_file_exists(full_path, description):
                self.check_python_syntax(full_path, description)
                # Only check imports for non-main files to avoid running servers
                if not file_path.endswith("main.py"):
                    self.check_python_imports(full_path, description)
        
        # Check HTML file
        html_path = f"{base_path}/ui/dashboard.html"
        if self.check_file_exists(html_path, "agentV1.2/ui/dashboard.html"):
            self.check_html_valid(html_path, "agentV1.2/ui/dashboard.html")
        
        # Check documentation files
        self.check_file_exists(f"{base_path}/supermemory.md", "agentV1.2/supermemory.md")
        self.check_file_exists(f"{base_path}/README.md", "agentV1.2/README.md")
        self.check_file_exists(f"{base_path}/requirements.txt", "agentV1.2/requirements.txt")
        
    def check_class_definitions(self):
        """Check specific class definitions exist"""
        
        # Check config has Config dataclass
        try:
            result = subprocess.run([
                'python3', '-c', '''
import sys
sys.path.insert(0, "/app/agentV1.2")
from config import Config, config
print("Config dataclass:", hasattr(Config, "__dataclass_fields__"))
print("Config instance:", hasattr(config, "OPENAI_API_KEY"))
'''
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and "Config dataclass: True" in result.stdout:
                self.log_test("agentV1.2/config.py has valid Config dataclass", True)
            else:
                self.log_test("agentV1.2/config.py has valid Config dataclass", False, result.stderr)
        except Exception as e:
            self.log_test("agentV1.2/config.py has valid Config dataclass", False, str(e))
        
        # Check other classes exist
        class_checks = [
            ("core/orchestrator.py", "Orchestrator", "core.orchestrator"),
            ("core/memory.py", "Memory", "core.memory"),
            ("core/intent.py", "IntentDetector", "core.intent"),
            ("events/bus.py", "EventBus", "events.bus"),
            ("agents/whatsapp_agent.py", "WhatsAppAgent", "agents.whatsapp_agent"),
            ("agents/blinkit_agent.py", "BlinkItAgent", "agents.blinkit_agent"),
            ("agents/browser_agent.py", "BrowserTaskAgent", "agents.browser_agent"),
        ]
        
        for file_path, class_name, module_path in class_checks:
            try:
                result = subprocess.run([
                    'python3', '-c', f'''
import sys
import os
sys.path.insert(0, "/app/agentV1.2")
os.chdir("/app/agentV1.2")
from {module_path} import {class_name}
print("Class {class_name} found and importable")
'''
                ], capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    self.log_test(f"{file_path} has valid {class_name} class", True)
                else:
                    self.log_test(f"{file_path} has valid {class_name} class", False, result.stderr.strip())
            except Exception as e:
                self.log_test(f"{file_path} has valid {class_name} class", False, str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("  AgentV1.2 Backend Testing")
        print("=" * 60)
        print(f"Testing backend URL: {BACKEND_URL}")
        print("-" * 60)
        
        # Test Blinkit2 APIs first
        print("\n🧪 Testing Blinkit2 APIs...")
        blinkit_health = self.test_blinkit2_health()
        blinkit_categories = self.test_blinkit2_categories()
        
        # Test agentV1.2 structure
        print("\n🧪 Testing agentV1.2 structure...")
        self.test_agentV1_2_structure()
        
        print("\n🧪 Testing agentV1.2 classes...")
        self.check_class_definitions()
        
        # Summary
        print("\n" + "=" * 60)
        print("  TEST SUMMARY")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Critical failures check
        critical_failures = []
        if not blinkit_health:
            critical_failures.append("Blinkit2 health API not working")
        if not blinkit_categories:
            critical_failures.append("Blinkit2 categories API not working")
            
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        print("\n📊 Results:")
        print(f"✅ Blinkit2 APIs: {'Working' if blinkit_health and blinkit_categories else 'FAILED'}")
        print(f"✅ AgentV1.2 Structure: {self.tests_passed - (2 if blinkit_health and blinkit_categories else (1 if blinkit_health or blinkit_categories else 0))}/{self.tests_run - 2} files valid")
        
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        if critical_failures:
            print(f"\n🚨 CRITICAL FAILURES:")
            for failure in critical_failures:
                print(f"  - {failure}")
            return False
            
        return len(failed_tests) == 0

def main():
    tester = BackendTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())