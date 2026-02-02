#!/usr/bin/env python3
"""
Test LDAP Connection Locally
Run before deploying to verify LDAP connectivity
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    from ldap3 import Server, Connection, ALL, SIMPLE
except ImportError:
    print("ERROR: ldap3 not installed")
    print("Install: pip3 install ldap3 --break-system-packages")
    sys.exit(1)

def test_ldap_connection():
    """Test basic LDAP connection"""
    print("=" * 60)
    print("LDAP CONNECTION TEST")
    print("=" * 60)
    
    config = {
        'host': os.getenv('LDAP_HOST'),
        'port': int(os.getenv('LDAP_PORT', 3268)),
        'username': os.getenv('LDAP_USERNAME'),
        'password': os.getenv('LDAP_PASSWORD'),
        'base_dn': os.getenv('LDAP_BASE_DN'),
    }
    
    print(f"\nHost: {config['host']}:{config['port']}")
    print(f"Username: {config['username']}")
    print(f"Base DN: {config['base_dn']}")
    
    try:
        server = Server(config['host'], port=config['port'], get_info=ALL)
        conn = Connection(
            server,
            user=config['username'],
            password=config['password'],
            authentication=SIMPLE,
            auto_bind=True
        )
        
        if conn.bound:
            print("\n✓ LDAP CONNECTION SUCCESSFUL")
            print(f"\nServer Info:\n{conn.server.info}")
            conn.unbind()
            return True
        else:
            print("\n✗ LDAP CONNECTION FAILED - Not bound")
            return False
            
    except Exception as e:
        print(f"\n✗ LDAP CONNECTION FAILED")
        print(f"Error: {str(e)}")
        return False

def test_user_lookup(username):
    """Test LDAP user lookup"""
    print("\n" + "=" * 60)
    print(f"LDAP USER LOOKUP: {username}")
    print("=" * 60)
    
    config = {
        'host': os.getenv('LDAP_HOST'),
        'port': int(os.getenv('LDAP_PORT', 3268)),
        'username': os.getenv('LDAP_USERNAME'),
        'password': os.getenv('LDAP_PASSWORD'),
    }
    
    # Determine if student or staff
    is_student = username.isnumeric()
    
    if is_student:
        search_tree = os.getenv('LDAP_STUDENT_TREE')
        print(f"Type: STUDENT")
    else:
        search_tree = os.getenv('LDAP_STAFF_TREE')
        print(f"Type: STAFF")
    
    print(f"Search Tree: {search_tree}")
    
    try:
        server = Server(config['host'], port=config['port'], get_info=ALL)
        conn = Connection(
            server,
            user=config['username'],
            password=config['password'],
            authentication=SIMPLE,
            auto_bind=True
        )
        
        search_filter = f"(sAMAccountName={username})"
        attrs = ['cn', 'displayName', 'givenName', 'sn', 'mail', 'sAMAccountName']
        
        conn.search(search_tree, search_filter, attributes=attrs)
        
        if conn.entries:
            print(f"\n✓ USER FOUND")
            for entry in conn.entries:
                print(f"\n{entry}")
        else:
            print(f"\n✗ USER NOT FOUND")
        
        conn.unbind()
        
    except Exception as e:
        print(f"\n✗ LOOKUP FAILED")
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    print("\n🔍 LDAP CONNECTIVITY TEST\n")
    
    # Test connection
    if test_ldap_connection():
        print("\n" + "=" * 60)
        
        # Test user lookups
        test_student = input("\nEnter student ID to test (or press Enter to skip): ").strip()
        if test_student:
            test_user_lookup(test_student)
        
        test_staff = input("\nEnter staff username to test (or press Enter to skip): ").strip()
        if test_staff:
            test_user_lookup(test_staff)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60 + "\n")