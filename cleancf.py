#!/usr/bin/env python3
"""
Script to list and delete all zones from Cloudflare account
"""

import time
import requests

# ===== API Configuration =====
CLOUDFLARE_EMAIL = "tmpcf1424@free.v.edu.kg"
CLOUDFLARE_API_KEY = "3ab3e76296fb4290b1b9dcaf6c0b608412cc3"
CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4/zones"

# Rate limiting
REQUEST_DELAY = 0.5  # seconds between API calls


def get_all_zones():
    """Fetch all zones from Cloudflare account"""
    headers = {
        "X-Auth-Email": CLOUDFLARE_EMAIL,
        "X-Auth-Key": CLOUDFLARE_API_KEY,
        "Content-Type": "application/json"
    }
    
    all_zones = []
    page = 1
    per_page = 50
    
    print("Fetching zones from Cloudflare...")
    
    while True:
        try:
            params = {
                "page": page,
                "per_page": per_page
            }
            response = requests.get(CLOUDFLARE_API_URL, headers=headers, params=params)
            data = response.json()
            
            if not data.get("success"):
                print(f"Error fetching zones: {data.get('errors')}")
                break
            
            zones = data.get("result", [])
            if not zones:
                break
            
            all_zones.extend(zones)
            print(f"  Fetched page {page}: {len(zones)} zones")
            
            # Check if there are more pages
            result_info = data.get("result_info", {})
            total_pages = result_info.get("total_pages", 1)
            if page >= total_pages:
                break
            
            page += 1
            time.sleep(REQUEST_DELAY)
            
        except Exception as e:
            print(f"Error: {e}")
            break
    
    return all_zones


def delete_zone(zone_id, zone_name):
    """Delete a single zone from Cloudflare"""
    headers = {
        "X-Auth-Email": CLOUDFLARE_EMAIL,
        "X-Auth-Key": CLOUDFLARE_API_KEY,
        "Content-Type": "application/json"
    }
    
    delete_url = f"{CLOUDFLARE_API_URL}/{zone_id}"
    
    try:
        response = requests.delete(delete_url, headers=headers)
        result = response.json()
        
        if result.get("success"):
            return True, "Success"
        else:
            error_msg = result.get("errors", [{}])[0].get("message", "Unknown error")
            return False, error_msg
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 70)
    print("Cloudflare Zone Cleanup Script")
    print("=" * 70)
    
    # Step 1: Fetch all zones
    zones = get_all_zones()
    
    if not zones:
        print("\nNo zones found in account.")
        return
    
    print(f"\n{'=' * 70}")
    print(f"Found {len(zones)} zone(s) in account:")
    print(f"{'=' * 70}")
    
    for i, zone in enumerate(zones, 1):
        print(f"{i}. {zone['name']} (ID: {zone['id']})")
    
    # Step 2: Confirm deletion
    print(f"\n{'=' * 70}")
    print("⚠️  WARNING: This will DELETE ALL zones listed above!")
    print("=" * 70)
    confirmation = input("\nType 'DELETE ALL' to confirm: ")
    
    if confirmation != "DELETE ALL":
        print("Deletion cancelled.")
        return
    
    # Step 3: Delete all zones
    print(f"\n{'=' * 70}")
    print("Starting deletion process...")
    print(f"{'=' * 70}\n")
    
    success_count = 0
    failed_count = 0
    
    for i, zone in enumerate(zones, 1):
        zone_name = zone['name']
        zone_id = zone['id']
        
        print(f"[{i}/{len(zones)}] Deleting {zone_name}...", end=' ')
        
        success, message = delete_zone(zone_id, zone_name)
        
        if success:
            print("✓ DELETED")
            success_count += 1
        else:
            print(f"✗ FAILED: {message}")
            failed_count += 1
        
        time.sleep(REQUEST_DELAY)
    
    # Step 4: Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY:")
    print(f"  Successfully deleted: {success_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(zones)}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()