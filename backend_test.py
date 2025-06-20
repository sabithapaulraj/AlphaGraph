
import requests
import json
import time
import os
from datetime import datetime

# Get the backend URL from the frontend .env file
def get_backend_url():
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    raise ValueError("Could not find REACT_APP_BACKEND_URL in frontend/.env")

# Main test class
class AlphaGraphAPITester:
    def __init__(self):
        self.base_url = f"{get_backend_url()}/api"
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": []
        }
        print(f"Testing API at: {self.base_url}")
    
    def run_test(self, test_name, test_func, *args, **kwargs):
        """Run a test and record results"""
        self.test_results["total_tests"] += 1
        print(f"\n{'='*80}\nRunning test: {test_name}\n{'='*80}")
        
        try:
            start_time = time.time()
            result = test_func(*args, **kwargs)
            end_time = time.time()
            
            if result["success"]:
                self.test_results["passed_tests"] += 1
                status = "PASSED"
            else:
                self.test_results["failed_tests"] += 1
                status = "FAILED"
                
            self.test_results["test_details"].append({
                "name": test_name,
                "status": status,
                "duration": round(end_time - start_time, 2),
                "details": result
            })
            
            print(f"Test {status}: {test_name}")
            if not result["success"]:
                print(f"Error: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            self.test_results["failed_tests"] += 1
            error_msg = str(e)
            self.test_results["test_details"].append({
                "name": test_name,
                "status": "FAILED",
                "details": {"success": False, "error": error_msg}
            })
            print(f"Test FAILED: {test_name}")
            print(f"Exception: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def test_root_endpoint(self):
        """Test the root API endpoint"""
        try:
            response = requests.get(f"{self.base_url}/")
            response.raise_for_status()
            data = response.json()
            
            if "message" in data and "AlphaGraph" in data["message"]:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": data
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": "Unexpected response format",
                    "response": data
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        try:
            response = requests.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            
            if "status" in data and data["status"] == "healthy":
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": data
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": "Health check failed",
                    "response": data
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_companies_endpoint(self):
        """Test the companies endpoint"""
        try:
            response = requests.get(f"{self.base_url}/companies")
            response.raise_for_status()
            data = response.json()
            
            if "companies" in data and isinstance(data["companies"], list) and len(data["companies"]) > 0:
                # Check if companies have the expected structure
                sample_company = data["companies"][0]
                if "symbol" in sample_company and "name" in sample_company:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "company_count": len(data["companies"]),
                        "sample_company": sample_company
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": "Company data missing required fields",
                        "sample_company": sample_company
                    }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": "Companies data missing or empty",
                    "response": data
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_analyze_endpoint(self):
        """Test the news analysis endpoint"""
        try:
            # Sample financial news
            test_data = {
                "headline": "Apple reports strong Q4 earnings with 12% revenue growth",
                "content": "Apple Inc. announced today strong fourth-quarter results with revenue of $94.9 billion, representing 12% year-over-year growth. iPhone sales exceeded expectations while Services revenue reached a new record high.",
                "source": "Test Source",
                "url": "https://example.com/test-article"
            }
            
            response = requests.post(
                f"{self.base_url}/analyze", 
                json=test_data
            )
            response.raise_for_status()
            data = response.json()
            
            # Check for required fields in the response
            required_fields = [
                "id", "headline", "content", "sentiment_score", 
                "sentiment_label", "impact_score", "key_points"
            ]
            
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                # Validate sentiment score is between -1 and 1
                if not (-1 <= data["sentiment_score"] <= 1):
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": f"Invalid sentiment score: {data['sentiment_score']}",
                        "response": data
                    }
                
                # Validate sentiment label
                valid_labels = ["BULLISH", "BEARISH", "NEUTRAL"]
                if data["sentiment_label"] not in valid_labels:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": f"Invalid sentiment label: {data['sentiment_label']}",
                        "response": data
                    }
                
                # Validate impact score is between 0 and 10
                if not (0 <= data["impact_score"] <= 10):
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": f"Invalid impact score: {data['impact_score']}",
                        "response": data
                    }
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "sentiment_score": data["sentiment_score"],
                    "sentiment_label": data["sentiment_label"],
                    "impact_score": data["impact_score"],
                    "mentioned_companies": data.get("mentioned_companies", []),
                    "key_points_count": len(data.get("key_points", [])),
                    "has_key_points": len(data.get("key_points", [])) > 0
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": f"Missing required fields: {', '.join(missing_fields)}",
                    "response": data
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_demo_populate_endpoint(self):
        """Test the demo data population endpoint"""
        try:
            response = requests.post(f"{self.base_url}/demo/populate")
            response.raise_for_status()
            data = response.json()
            
            if "message" in data and "analyses" in data:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "analyses_count": data["analyses"],
                    "message": data["message"]
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": "Unexpected response format",
                    "response": data
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_recent_news_endpoint(self):
        """Test the recent news endpoint"""
        try:
            # First ensure we have some data
            self.test_demo_populate_endpoint()
            
            # Now test the recent news endpoint
            response = requests.get(f"{self.base_url}/news/recent")
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                if len(data) > 0:
                    # Check if the first item has the expected structure
                    sample_item = data[0]
                    required_fields = [
                        "id", "headline", "content", "sentiment_score", 
                        "sentiment_label", "impact_score"
                    ]
                    
                    missing_fields = [field for field in required_fields if field not in sample_item]
                    
                    if not missing_fields:
                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "news_count": len(data),
                            "sample_item": {k: sample_item[k] for k in ["headline", "sentiment_label", "impact_score"]}
                        }
                    else:
                        return {
                            "success": False,
                            "status_code": response.status_code,
                            "error": f"Missing required fields in news item: {', '.join(missing_fields)}",
                            "sample_item": sample_item
                        }
                else:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "news_count": 0,
                        "message": "No news items found, but endpoint is working"
                    }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": "Expected a list of news items",
                    "response": data
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_trends_endpoint(self):
        """Test the trends endpoint"""
        try:
            # First ensure we have some data
            self.test_demo_populate_endpoint()
            
            # Now test the trends endpoint
            response = requests.get(f"{self.base_url}/trends")
            response.raise_for_status()
            data = response.json()
            
            required_fields = ["trending_companies", "analysis_period", "total_analyses"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "trending_companies_count": len(data["trending_companies"]),
                    "analysis_period": data["analysis_period"],
                    "total_analyses": data["total_analyses"]
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": f"Missing required fields: {', '.join(missing_fields)}",
                    "response": data
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_all_tests(self):
        """Run all API tests"""
        print(f"Starting AlphaGraph API tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test basic endpoints
        self.run_test("Root Endpoint", self.test_root_endpoint)
        self.run_test("Health Endpoint", self.test_health_endpoint)
        self.run_test("Companies Endpoint", self.test_companies_endpoint)
        
        # Test core functionality
        self.run_test("Demo Data Population", self.test_demo_populate_endpoint)
        self.run_test("AI Analysis", self.test_analyze_endpoint)
        self.run_test("Recent News Retrieval", self.test_recent_news_endpoint)
        self.run_test("Trending Analysis", self.test_trends_endpoint)
        
        # Print summary
        print("\n" + "="*80)
        print(f"TEST SUMMARY: {self.test_results['passed_tests']}/{self.test_results['total_tests']} tests passed")
        print("="*80)
        
        for test in self.test_results["test_details"]:
            print(f"{test['status']}: {test['name']}")
        
        return self.test_results

if __name__ == "__main__":
    tester = AlphaGraphAPITester()
    results = tester.run_all_tests()
    
    # Save results to file
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nTest results saved to /app/backend_test_results.json")
    
    # Exit with appropriate code
    if results["failed_tests"] > 0:
        print(f"\n{results['failed_tests']} tests failed!")
        exit(1)
    else:
        print("\nAll tests passed!")
        exit(0)
