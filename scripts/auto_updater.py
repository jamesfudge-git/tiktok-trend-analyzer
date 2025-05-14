#!/usr/bin/env python3
# scripts/auto_updater.py
import os
import sys
import time
import datetime
import logging
from pathlib import Path

# Import our analyzer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.hourly_update import TrendAnalyzer
from scripts.ai_analyzer import AITrendAnalyzer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("updater.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutoUpdater")

class AutoUpdater:
    def __init__(self, update_interval=3600):
        """
        Initialize the auto updater
        update_interval: time in seconds between updates (default: 3600 = 1 hour)
        """
        self.update_interval = update_interval
        self.analyzer = TrendAnalyzer()
        self.ai_analyzer = AITrendAnalyzer()
        self.running = False
        
    def start(self):
        """Start the automatic update loop"""
        self.running = True
        logger.info(f"Starting automatic updater with {self.update_interval} seconds interval")
        
        try:
            while self.running:
                # Run the update
                logger.info("Running scheduled update...")
                self.run_update()
                
                # Calculate next update time
                next_update = datetime.datetime.now() + datetime.timedelta(seconds=self.update_interval)
                logger.info(f"Next update scheduled for: {next_update}")
                
                # Sleep until next update
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            logger.info("Automatic updater stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Error in update loop: {e}")
            self.running = False
    
    def run_update(self):
        """Run a single update cycle"""
        try:
            # Run the trend analysis pipeline
            success = self.analyzer.run_pipeline()
            
            if success:
                logger.info("Pipeline update successful")
                
                # Run AI analysis if pipeline succeeded
                try:
                    self.ai_analyzer.analyze()
                    logger.info("AI analysis completed")
                except Exception as e:
                    logger.error(f"Error in AI analysis: {e}")
            else:
                logger.warning("Pipeline update reported failure, skipping AI analysis")
                
            return success
        except Exception as e:
            logger.error(f"Error running update: {e}")
            return False

if __name__ == "__main__":
    # Create and start the auto updater
    updater = AutoUpdater()
    updater.start()