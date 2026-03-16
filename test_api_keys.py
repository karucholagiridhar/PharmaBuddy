"""
API Key Validation Script
Tests all configured API keys to ensure they work properly
"""

import sys
import os
from datetime import datetime

# Fix encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add utils to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import Config
from utils.utils import setup_logger

logger = setup_logger("API_TEST")

class APIKeyTester:
    def __init__(self):
        self.results = []
        self.status = "✓"
        self.failed_count = 0
        self.success_count = 0

    def test_google_api_key(self):
        """Test Google API Key"""
        print("\n" + "="*60)
        print("Testing GOOGLE_API_KEY")
        print("="*60)

        try:
            if not Config.GOOGLE_API_KEY:
                self.log_result("GOOGLE_API_KEY", False, "API key not configured in .env")
                return

            from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

            # Test embeddings
            try:
                embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/gemini-embedding-001",
                    google_api_key=Config.GOOGLE_API_KEY
                )
                test_embedding = embeddings.embed_query("test")
                if test_embedding and len(test_embedding) > 0:
                    self.log_result("Google Embeddings API", True,
                        f"Working - Embedding dimension: {len(test_embedding)}")
                else:
                    self.log_result("Google Embeddings API", False, "No embedding returned")
            except Exception as e:
                self.log_result("Google Embeddings API", False, str(e))
                return

            # Test Chat API
            try:
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash-lite",
                    google_api_key=Config.GOOGLE_API_KEY
                )
                response = llm.invoke("Say 'API is working' in one word.")
                if response and hasattr(response, 'content'):
                    self.log_result("Google Chat API (Gemini)", True,
                        f"Working - Response: {response.content[:30]}...")
                else:
                    self.log_result("Google Chat API (Gemini)", False, "No response from API")
            except Exception as e:
                self.log_result("Google Chat API (Gemini)", False, str(e))

        except Exception as e:
            self.log_result("GOOGLE_API_KEY", False, f"Import/Setup Error: {str(e)}")

    def test_pinecone_api_key(self):
        """Test Pinecone API Key"""
        print("\n" + "="*60)
        print("Testing PINECONE_API_KEY")
        print("="*60)

        try:
            if not Config.PINECONE_API_KEY:
                self.log_result("PINECONE_API_KEY", False, "API key not configured in .env")
                return

            from pinecone import Pinecone

            pc = Pinecone(api_key=Config.PINECONE_API_KEY)

            # Test connection by listing indexes
            indexes = pc.list_indexes()
            if hasattr(indexes, 'names'):
                index_list = list(indexes.names())
                found = Config.PINECONE_INDEX_NAME in index_list
                if found:
                    self.log_result("Pinecone Connection", True,
                        f"Working - Index '{Config.PINECONE_INDEX_NAME}' found")
                else:
                    self.log_result("Pinecone Connection", True,
                        f"Working - Connected but index '{Config.PINECONE_INDEX_NAME}' not found (will be created on first use). Available: {index_list}")
            else:
                self.log_result("Pinecone Connection", True, "Connected successfully")

        except Exception as e:
            self.log_result("PINECONE_API_KEY", False, str(e))

    def test_mongo_uri(self):
        """Test MongoDB Connection"""
        print("\n" + "="*60)
        print("Testing MONGO_URI")
        print("="*60)

        try:
            if not Config.MONGO_URI:
                self.log_result("MONGO_URI", False, "MongoDB URI not configured in .env")
                return

            from pymongo import MongoClient
            import socket

            # Test connection with timeout
            client = MongoClient(Config.MONGO_URI, **Config.get_tls_kwargs())

            # Attempt to connect
            try:
                client.admin.command('ping')
                self.log_result("MongoDB Connection", True, "Ping successful - Database is accessible")

                # Try to access the database
                db = client.get_database("prescription_db")
                collections = db.list_collection_names()
                self.log_result("MongoDB Database Access", True,
                    f"Database accessible - Collections: {collections if collections else 'None yet'}")

            except socket.timeout:
                self.log_result("MongoDB Connection", False,
                    "Connection timeout - Database server may be unreachable")
            except Exception as e:
                self.log_result("MongoDB Connection", False, str(e))
            finally:
                client.close()

        except Exception as e:
            self.log_result("MONGO_URI", False, f"Setup Error: {str(e)}")

    def test_email_config(self):
        """Test Email Configuration"""
        print("\n" + "="*60)
        print("Testing EMAIL Configuration")
        print("="*60)

        try:
            email_sender = Config.EMAIL_SENDER
            email_password = Config.EMAIL_PASSWORD

            if not email_sender:
                self.log_result("EMAIL_SENDER", False, "Not configured in .env")
            else:
                self.log_result("EMAIL_SENDER", True, f"Configured: {email_sender}")

            if not email_password:
                self.log_result("EMAIL_PASSWORD", False, "Not configured in .env")
            else:
                self.log_result("EMAIL_PASSWORD", True, "Configured (hidden)")

                # Optional: Test SMTP connection
                try:
                    import smtplib
                    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=5)
                    server.starttls()
                    server.login(email_sender, email_password)
                    server.quit()
                    self.log_result("Gmail SMTP Connection", True, "SMTP login successful")
                except Exception as e:
                    self.log_result("Gmail SMTP Connection", False,
                        f"SMTP connection failed: {str(e)}")

        except Exception as e:
            self.log_result("EMAIL Configuration", False, f"Setup Error: {str(e)}")

    def log_result(self, service_name, success, message):
        """Log test result"""
        status = "[PASS]" if success else "[FAIL]"
        print(f"\n{status}: {service_name}")
        print(f"    Details: {message}")

        self.results.append({
            "service": service_name,
            "status": success,
            "message": message
        })

        if success:
            self.success_count += 1
        else:
            self.failed_count += 1

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        for result in self.results:
            status = "[OK]" if result["status"] else "[FAIL]"
            print(f"{status} {result['service']}: {result['message'][:50]}...")

        print("\n" + "-"*60)
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {self.success_count}")
        print(f"Failed: {self.failed_count}")
        print(f"Success Rate: {(self.success_count / len(self.results) * 100):.1f}%")

        if self.failed_count > 0:
            print("\n[WARNING] Some API keys are not working properly!")
            print("Please check the failed services above.")
        else:
            print("\n[SUCCESS] All API keys are working properly!")

        print("="*60)

    def run_all_tests(self):
        """Run all API key tests"""
        print("\n" + "="*60)
        print(f"PharmaBuddy API KEY VALIDATION TEST")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        self.test_google_api_key()
        self.test_pinecone_api_key()
        self.test_mongo_uri()
        self.test_email_config()

        self.print_summary()

        return self.failed_count == 0


if __name__ == "__main__":
    tester = APIKeyTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
