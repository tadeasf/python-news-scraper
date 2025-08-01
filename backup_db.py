#!/usr/bin/env python3
"""
Simple database backup script.
"""

import shutil
from datetime import datetime
from pathlib import Path

def backup_database():
    """Create a backup of the database."""
    db_file = Path("news_scraper.db")
    
    if db_file.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = Path(f"news_scraper_backup_{timestamp}.db")
        
        shutil.copy2(db_file, backup_file)
        print(f"Database backed up to: {backup_file}")
        return backup_file
    else:
        print("No database file found to backup")
        return None

if __name__ == "__main__":
    backup_database()