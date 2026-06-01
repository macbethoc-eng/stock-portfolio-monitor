#!/usr/bin/env python3
"""
Generate and send the stock opportunities report.
Run daily at 4pm ET.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.report_generator import generate_opportunity_report
from src.emailer import send_opportunity_report

def main():
    print("Generating stock opportunities report...")
    result = generate_opportunity_report()
    print(f"Report generated: {result['sectors_identified']} sectors, {len(result.get('trending_topics', []))} trending topics")
    
    print("Sending email...")
    success = send_opportunity_report(result['report'])
    if success:
        print("Email sent successfully!")
    else:
        print("Email failed - check himalaya configuration")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())