#!/usr/bin/env python3
"""
Test Strathmore Dataservices Locally
Run this before deploying to verify API connectivity
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def test_student_service():
    """Test student dataservice"""
    print("=" * 60)
    print("STUDENT DATASERVICE TEST")
    print("=" * 60)
    
    base_url = os.getenv('STUDENT_DATASERVICE_URL')
    print(f"\nBase URL: {base_url}")
    
    endpoints = [
        ('getAllSchools', 'Get All Schools'),
        ('getAllAcademicYears', 'Get Academic Years'),
        ('getAllIntakes', 'Get Intakes'),
        ('getAllCurrentStudents', 'Get All Students'),
    ]
    
    for endpoint, description in endpoints:
        url = f'{base_url}{endpoint}'
        print(f"\n→ Testing: {description}")
        print(f"  URL: {url}")
        
        try:
            response = requests.get(url, timeout=10, verify=True)
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ SUCCESS ({response.elapsed.total_seconds():.2f}s)")
                print(f"  Records: {len(data) if isinstance(data, list) else 'N/A'}")
            else:
                print(f"  ✗ FAILED: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"  ✗ TIMEOUT (>10s)")
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")

def test_staff_service():
    """Test staff dataservice"""
    print("\n" + "=" * 60)
    print("STAFF DATASERVICE TEST")
    print("=" * 60)
    
    base_url = os.getenv('STAFF_DATASERVICE_URL')
    print(f"\nBase URL: {base_url}")
    
    endpoints = [
        ('getAllDepartments', 'Get All Departments'),
        ('getAllStaff', 'Get All Staff'),
    ]
    
    for endpoint, description in endpoints:
        url = f'{base_url}{endpoint}'
        print(f"\n→ Testing: {description}")
        print(f"  URL: {url}")
        
        try:
            response = requests.get(url, timeout=10, verify=True)
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ SUCCESS ({response.elapsed.total_seconds():.2f}s)")
                print(f"  Records: {len(data) if isinstance(data, list) else 'N/A'}")
            else:
                print(f"  ✗ FAILED: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"  ✗ TIMEOUT (>10s)")
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")

def test_specific_staff():
    """Test fetching specific staff by username"""
    print("\n" + "=" * 60)
    print("STAFF BY USERNAME TEST")
    print("=" * 60)
    
    base_url = os.getenv('STAFF_DATASERVICE_URL')
    
    # Replace with real staff username for testing
    test_username = input("\nEnter staff username to test (or press Enter to skip): ").strip()
    
    if not test_username:
        print("  Skipped.")
        return
    
    url = f'{base_url}getStaffByUsername/{test_username}'
    print(f"\nURL: {url}")
    
    try:
        response = requests.get(url, timeout=10, verify=True)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ SUCCESS")
            print(f"  Data: {data}")
        else:
            print(f"  ✗ FAILED: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"  ✗ ERROR: {str(e)}")

if __name__ == '__main__':
    print("\n STRATHMORE DATASERVICE CONNECTIVITY TEST\n")
    
    # Test student service
    test_student_service()
    
    # Test staff service
    test_staff_service()
    
    # Test specific staff lookup
    test_specific_staff()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\n!! TIP: If tests fail, set DATASERVICE_USE_MOCK=true in .env")
    print("   This will use mock data as fallback.\n")