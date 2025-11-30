#!/usr/bin/env python3
"""
Script to test Cloudflare subdomain registration for NXDOMAIN base domains
"""

import os
import json
import time
import dns.resolver
import requests
from pathlib import Path

# ===== API Configuration =====
CLOUDFLARE_EMAIL = "tmpcf1424@free.v.edu.kg"
CLOUDFLARE_API_KEY = "3ab3e76296fb4290b1b9dcaf6c0b608412cc3"
CLOUDFLARE_ACCOUNT_ID = "b7b45c1d79740b7c18549879de5cb348"
CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4/zones"

# ===== File Paths =====
REPO_PATH = "Site-Subdomains"
DOMAINS_DIR = f"{REPO_PATH}/Domains"
BASE_DOMAINS_CACHE = "base_domains.txt"
NXDOMAIN_CACHE = "nxdomain_base_domains.txt"
FAILED_LOG = "add_cf_failed.txt"
SUCCESS_LOG = "add_cf_success.txt"

# Subdomain prefix to test
SUBDOMAIN_PREFIX = "exsub"

# Rate limiting
REQUEST_DELAY = 1.0  # seconds between API calls


def clone_repo():
    """Clone the repository if it doesn't exist"""
    if not os.path.exists(REPO_PATH):
        print("Cloning repository...")
        os.system("git clone https://github.com/Hollow667/Site-Subdomains.git")
    else:
        print("Repository already exists, skipping clone.")


def get_base_domains():
    """Get list of domain filenames from Domains directory"""
    if os.path.exists(BASE_DOMAINS_CACHE):
        print(f"Loading base domains from cache: {BASE_DOMAINS_CACHE}")
        with open(BASE_DOMAINS_CACHE, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    
    print("Scanning Domains directory for filenames...")
    domains = []
    domains_path = Path(DOMAINS_DIR)
    
    if not domains_path.exists():
        print(f"Error: {DOMAINS_DIR} not found!")
        return []
    
    for file in domains_path.iterdir():
        if file.is_file():
            domains.append(file.name)
    
    # Save to cache
    print(f"Saving {len(domains)} domains to cache: {BASE_DOMAINS_CACHE}")
    with open(BASE_DOMAINS_CACHE, 'w') as f:
        for domain in domains:
            f.write(f"{domain}\n")
    
    return domains


def check_dns_exists(domain):
    """Check if domain has NS records (resolves without NXDOMAIN error)"""
    try:
        dns.resolver.resolve(domain, 'NS')
        return True  # Domain resolves, has NS records
    except dns.resolver.NXDOMAIN:
        return False  # Domain doesn't exist
    except dns.resolver.NoAnswer:
        return False  # No NS records
    except dns.resolver.Timeout:
        print(f"  Timeout checking {domain}, treating as existing")
        return True  # Conservative: assume exists on timeout
    except Exception as e:
        print(f"  Error checking {domain}: {e}, treating as existing")
        return True  # Conservative: assume exists on error


def get_nxdomain_domains(base_domains):
    """Filter domains to only those that are NXDOMAIN"""
    if os.path.exists(NXDOMAIN_CACHE):
        print(f"Loading NXDOMAIN domains from cache: {NXDOMAIN_CACHE}")
        with open(NXDOMAIN_CACHE, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    
    print("Checking DNS for NXDOMAIN domains...")
    nxdomains = []
    
    for i, domain in enumerate(base_domains, 1):
        print(f"[{i}/{len(base_domains)}] Checking {domain}...", end=' ')
        if not check_dns_exists(domain):
            print("NXDOMAIN ✓")
            nxdomains.append(domain)
        else:
            print("EXISTS (skipping)")
        time.sleep(0.1)  # Small delay to avoid hammering DNS
    
    # Save to cache
    print(f"\nSaving {len(nxdomains)} NXDOMAIN domains to cache: {NXDOMAIN_CACHE}")
    with open(NXDOMAIN_CACHE, 'w') as f:
        for domain in nxdomains:
            f.write(f"{domain}\n")
    
    return nxdomains


def append_to_file(filename, content):
    """Append content to file (create if doesn't exist)"""
    with open(filename, 'a') as f:
        f.write(content + '\n')


def add_zone_to_cloudflare(zone_name):
    """Attempt to add a zone to Cloudflare account"""
    headers = {
        "X-Auth-Email": CLOUDFLARE_EMAIL,
        "X-Auth-Key": CLOUDFLARE_API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "account": {"id": CLOUDFLARE_ACCOUNT_ID},
        "name": zone_name,
        "jump_start": True
    }
    
    try:
        response = requests.post(CLOUDFLARE_API_URL, headers=headers, json=data)
        return response.json()
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}


def delete_zone_from_cloudflare(zone_id):
    """Delete a zone from Cloudflare account"""
    headers = {
        "X-Auth-Email": CLOUDFLARE_EMAIL,
        "X-Auth-Key": CLOUDFLARE_API_KEY,
        "Content-Type": "application/json"
    }
    
    delete_url = f"{CLOUDFLARE_API_URL}/{zone_id}"
    
    try:
        response = requests.delete(delete_url, headers=headers)
        return response.json()
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}


def test_cloudflare_registration(nxdomain_domains):
    """Test Cloudflare registration for constructed subdomains"""
    print(f"\nTesting Cloudflare registration for {len(nxdomain_domains)} domains...")
    
    success_count = 0
    failed_count = 0
    
    for i, domain in enumerate(nxdomain_domains, 1):
        subdomain = f"{SUBDOMAIN_PREFIX}.{domain}"
        print(f"\n[{i}/{len(nxdomain_domains)}] Testing: {subdomain}")
        
        result = add_zone_to_cloudflare(subdomain)
        
        if result.get("success"):
            print(f"  ✓ SUCCESS!")
            success_count += 1
            # Append to success log
            log_entry = f"{subdomain} | {json.dumps(result)}"
            append_to_file(SUCCESS_LOG, log_entry)
            
            # Immediately delete the zone
            zone_id = result.get("result", {}).get("id")
            if zone_id:
                print(f"  → Deleting zone {zone_id}...", end=' ')
                delete_result = delete_zone_from_cloudflare(zone_id)
                if delete_result.get("success"):
                    print("DELETED ✓")
                else:
                    delete_error = delete_result.get("errors", [{}])[0].get("message", "Unknown error")
                    print(f"DELETE FAILED: {delete_error}")
            else:
                print(f"  ⚠ No zone ID returned, cannot delete")
        else:
            error_msg = result.get("errors", [{}])[0].get("message", "Unknown error")
            print(f"  ✗ FAILED: {error_msg}")
            failed_count += 1
            # Append to failed log
            log_entry = f"{subdomain} | {json.dumps(result)}"
            append_to_file(FAILED_LOG, log_entry)
        
        # Rate limiting
        time.sleep(REQUEST_DELAY)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Success: {success_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(nxdomain_domains)}")
    print(f"{'='*60}")
    print(f"\nResults saved to:")
    print(f"  - {SUCCESS_LOG}")
    print(f"  - {FAILED_LOG}")


def main():
    print("=" * 60)
    print("Cloudflare Subdomain Registration Tester")
    print("=" * 60)
    
    # Step 1: Clone repository
    clone_repo()
    
    # Step 2: Get base domains from filenames
    base_domains = get_base_domains()
    if not base_domains:
        print("No domains found!")
        return
    print(f"\nFound {len(base_domains)} base domains")
    
    # Step 3: Filter to NXDOMAIN only
    nxdomain_domains = get_nxdomain_domains(base_domains)
    if not nxdomain_domains:
        print("No NXDOMAIN domains found!")
        return
    print(f"\nFound {len(nxdomain_domains)} NXDOMAIN domains")
    
    # Step 4: Test Cloudflare registration
    test_cloudflare_registration(nxdomain_domains)


if __name__ == "__main__":
    main()