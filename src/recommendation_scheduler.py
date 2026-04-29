"""
Recommendation System Scheduler
Handles weekly automatic updates of user recommendations

Features:
- Scheduled weekly updates for all users
- Batch processing with configurable chunk size
- Error handling and logging
- Can be run as standalone service or cron job
"""

import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional
import argparse

from recommendation_engine import RecommendationManager, load_recommendation_system


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RecommendationScheduler:
    """
    Manages scheduled updates of recommendations for all users.
    """
    
    def __init__(self, manager: RecommendationManager, users_df):
        self.manager = manager
        self.users = users_df['user_id'].tolist()
        self.total_users = len(self.users)
        logger.info(f"Scheduler initialized for {self.total_users} users")
    
    def update_user_recommendations(self, user_id: str) -> bool:
        """
        Update recommendations for a single user.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if update is needed
            if not self.manager._should_refresh(user_id):
                logger.debug(f"Skipping {user_id} - not due for update")
                return True
            
            logger.info(f"Updating recommendations for {user_id}")
            recommendations = self.manager.get_recommendations(user_id, force_refresh=True)
            logger.info(f"Generated {len(recommendations)} recommendations for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating {user_id}: {e}")
            return False
    
    def update_all_users(self, chunk_size: int = 100):
        """
        Update recommendations for all users in batches.
        
        Args:
            chunk_size: Number of users to process in each batch
        """
        logger.info(f"Starting batch update for {self.total_users} users (chunk_size={chunk_size})")
        start_time = datetime.utcnow()
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for i in range(0, self.total_users, chunk_size):
            chunk = self.users[i:i+chunk_size]
            logger.info(f"Processing chunk {i//chunk_size + 1}/{(self.total_users + chunk_size - 1)//chunk_size}")
            
            for user_id in chunk:
                if self.update_user_recommendations(user_id):
                    success_count += 1
                else:
                    error_count += 1
            
            # Small delay between chunks to avoid overwhelming the system
            time.sleep(1)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"Batch update completed in {duration:.2f}s")
        logger.info(f"Results: {success_count} successful, {error_count} errors, {skipped_count} skipped")
        
        return {
            'total_users': self.total_users,
            'success': success_count,
            'errors': error_count,
            'skipped': skipped_count,
            'duration_seconds': duration
        }
    
    def update_active_users_only(self, days_threshold: int = 30):
        """
        Update only active users (those who logged in recently).
        
        Args:
            days_threshold: Number of days to consider user as active
        """
        # This would filter based on last_login from database
        # For now, update all users
        logger.info(f"Updating active users (last {days_threshold} days)")
        return self.update_all_users()
    
    def update_due_users_only(self):
        """
        Update only users whose recommendations are due for refresh.
        """
        logger.info("Updating only users due for refresh")
        
        due_users = []
        for user_id in self.users:
            if self.manager._should_refresh(user_id):
                due_users.append(user_id)
        
        logger.info(f"Found {len(due_users)} users due for update")
        
        success_count = 0
        error_count = 0
        
        for user_id in due_users:
            if self.update_user_recommendations(user_id):
                success_count += 1
            else:
                error_count += 1
        
        logger.info(f"Updated {success_count} users, {error_count} errors")
        
        return {
            'total_due': len(due_users),
            'success': success_count,
            'errors': error_count
        }


def schedule_weekly_updates(scheduler: RecommendationScheduler):
    """
    Set up weekly scheduled updates.
    
    Runs every Sunday at 2 AM.
    """
    schedule.every().sunday.at("02:00").do(scheduler.update_due_users_only)
    logger.info("Weekly schedule configured: Every Sunday at 2:00 AM")


def schedule_daily_check(scheduler: RecommendationScheduler):
    """
    Set up daily checks for due updates.
    
    Runs every day at 3 AM.
    """
    schedule.every().day.at("03:00").do(scheduler.update_due_users_only)
    logger.info("Daily schedule configured: Every day at 3:00 AM")


def run_scheduler(data_path: str, mode: str = "weekly"):
    """
    Run the recommendation scheduler.
    
    Args:
        data_path: Path to the data directory
        mode: "weekly", "daily", or "once"
    """
    logger.info(f"Starting recommendation scheduler in {mode} mode")
    
    # Load recommendation system
    logger.info("Loading recommendation system...")
    manager = load_recommendation_system(data_path)
    
    # Load users
    import pandas as pd
    import os
    users_df = pd.read_csv(os.path.join(data_path, 'users.csv'))
    
    # Initialize scheduler
    scheduler = RecommendationScheduler(manager, users_df)
    
    if mode == "once":
        # Run once and exit
        logger.info("Running one-time update...")
        results = scheduler.update_due_users_only()
        logger.info(f"One-time update completed: {results}")
        return
    
    elif mode == "weekly":
        schedule_weekly_updates(scheduler)
    
    elif mode == "daily":
        schedule_daily_check(scheduler)
    
    elif mode == "test":
        # Run every minute for testing
        schedule.every(1).minutes.do(scheduler.update_due_users_only)
        logger.info("Test schedule: Every 1 minute")
    
    else:
        logger.error(f"Unknown mode: {mode}")
        return
    
    # Run scheduler loop
    logger.info("Scheduler running. Press Ctrl+C to exit.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recommendation System Scheduler")
    parser.add_argument(
        "--data-path",
        default="./out_small",
        help="Path to the data directory"
    )
    parser.add_argument(
        "--mode",
        choices=["once", "daily", "weekly", "test"],
        default="weekly",
        help="Scheduler mode: once (run once), daily, weekly, or test"
    )
    
    args = parser.parse_args()
    
    run_scheduler(args.data_path, args.mode)
