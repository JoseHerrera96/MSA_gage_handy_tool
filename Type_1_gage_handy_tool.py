"""Generate Gage Study Report (one-time, no monitoring)."""

import pandas as pd
import time
from Gage_report import SimplifiedGageReporter

if __name__ == "__main__":
    FILE = "gage data.txt"
    OUT = "Gage_Study_Summary.txt"
    
    print("Generating Gage Study Report...")
    event_handler = SimplifiedGageReporter(FILE, OUT)
    event_handler.generate_report()
    print(f"[OK] Report written to {OUT}")
    print(f"[OK] Dashboard created at {OUT.replace('.txt', '_dashboard.html')}")
