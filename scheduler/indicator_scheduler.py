import schedule
import time
import logging
from datetime import datetime, time as dt_time
from typing import Optional
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.config.config_manager import ConfigManager
from src.composer.main_composer import MainComposer
from src.storage.database import IndicatorDatabase
from src.storage.file_logger import FileLogger

class IndicatorScheduler:
    def __init__(self):
        self.logger = self._setup_logging()
        self.config = ConfigManager()
        self.composer = MainComposer(self.config)
        self.database = IndicatorDatabase()
        self.file_logger = FileLogger()

        # Scheduled times (08:00 and 20:00)
        self.scheduled_times = ["08:00", "20:00"]

        self.logger.info("Indicator Scheduler initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scheduler.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def run_indicators_calculation(self):
        """Run the complete indicators calculation"""
        try:
            self.logger.info("="*60)
            self.logger.info("STARTING SCHEDULED INDICATOR CALCULATION")
            self.logger.info("="*60)

            # Log system status
            self.database.log_system_event(
                level="INFO",
                component="scheduler",
                message="Starting scheduled calculation",
                details={"scheduled_time": datetime.now().isoformat()}
            )

            # Run the calculation
            results = self.composer.calculate_both_indicators(refresh_data=True)

            if 'error' in results:
                self.logger.error(f"Calculation failed: {results['error']}")
                self.database.log_system_event(
                    level="ERROR",
                    component="scheduler",
                    message="Calculation failed",
                    details={"error": results['error']}
                )
                return False

            # Store results in database
            calculation_id = self.database.store_calculation(results)
            if calculation_id:
                self.logger.info(f"Results stored in database with ID: {calculation_id}")
            else:
                self.logger.warning("Failed to store results in database")

            # Export to JSON
            json_file = self.file_logger.log_calculation_json(results)
            if json_file:
                self.logger.info(f"Results exported to JSON: {json_file}")

            # Export to CSV
            csv_timestamp = self.file_logger.log_calculation_csv(results)
            if csv_timestamp:
                self.logger.info(f"Results exported to CSV files: {csv_timestamp}")

            # Append to historical data
            self.file_logger.append_to_historical_csv(results)

            # Create Excel report (optional - can be resource intensive)
            # excel_file = self.file_logger.create_excel_report(results)
            # if excel_file:
            #     self.logger.info(f"Excel report created: {excel_file}")

            # Log successful completion
            self.database.log_system_event(
                level="INFO",
                component="scheduler",
                message="Calculation completed successfully",
                details={
                    "calculation_id": calculation_id,
                    "bottom_score": results.get('bottom_analysis', {}).get('composite_score'),
                    "top_score": results.get('top_analysis', {}).get('composite_score'),
                    "duration_seconds": results.get('calculation_info', {}).get('duration_seconds')
                }
            )

            self.logger.info("="*60)
            self.logger.info("SCHEDULED CALCULATION COMPLETED SUCCESSFULLY")
            self.logger.info("="*60)

            return True

        except Exception as e:
            self.logger.error(f"Error in scheduled calculation: {e}")
            self.database.log_system_event(
                level="ERROR",
                component="scheduler",
                message="Unexpected error in calculation",
                details={"error": str(e)}
            )
            return False

    def setup_schedule(self):
        """Setup the scheduling for twice-daily execution"""
        try:
            # Schedule for 08:00
            schedule.every().day.at("08:00").do(self.run_indicators_calculation)

            # Schedule for 20:00
            schedule.every().day.at("20:00").do(self.run_indicators_calculation)

            self.logger.info("Scheduled jobs:")
            self.logger.info("- Daily at 08:00 UTC")
            self.logger.info("- Daily at 20:00 UTC")

            # Log schedule setup
            self.database.log_system_event(
                level="INFO",
                component="scheduler",
                message="Scheduler setup completed",
                details={"scheduled_times": self.scheduled_times}
            )

        except Exception as e:
            self.logger.error(f"Error setting up schedule: {e}")
            raise

    def run_scheduler(self):
        """Run the scheduler (blocking)"""
        try:
            self.setup_schedule()

            self.logger.info("Scheduler started. Waiting for scheduled times...")
            self.logger.info("Press Ctrl+C to stop the scheduler")

            # Run immediate calculation if requested
            current_time = datetime.now().time()
            scheduled_times_dt = [dt_time.fromisoformat(t) for t in self.scheduled_times]

            # Check if we're close to a scheduled time (within 10 minutes)
            for sched_time in scheduled_times_dt:
                time_diff = abs(
                    (current_time.hour * 60 + current_time.minute) -
                    (sched_time.hour * 60 + sched_time.minute)
                )
                if time_diff <= 10:  # Within 10 minutes
                    self.logger.info(f"Close to scheduled time {sched_time}, running immediate calculation")
                    self.run_indicators_calculation()
                    break

            # Main scheduler loop
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")
            self.database.log_system_event(
                level="INFO",
                component="scheduler",
                message="Scheduler stopped by user"
            )
        except Exception as e:
            self.logger.error(f"Error in scheduler: {e}")
            self.database.log_system_event(
                level="ERROR",
                component="scheduler",
                message="Scheduler error",
                details={"error": str(e)}
            )
            raise

    def run_manual_calculation(self):
        """Run a manual calculation (for testing)"""
        self.logger.info("Running manual calculation...")
        return self.run_indicators_calculation()

    def cleanup_old_data(self, days: int = 90):
        """Clean up old data"""
        try:
            self.logger.info(f"Cleaning up data older than {days} days...")
            self.database.cleanup_old_data(days)
            self.logger.info("Data cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def get_system_status(self) -> dict:
        """Get system status information"""
        try:
            status = {
                "scheduler_running": True,
                "next_scheduled_runs": [str(job.next_run) for job in schedule.jobs],
                "database_stats": self.database.get_database_stats(),
                "cache_status": self.composer.tf_manager.get_cache_status(),
                "system_time": datetime.now().isoformat()
            }
            return status
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}

def main():
    """Main entry point for the scheduler"""
    import argparse

    parser = argparse.ArgumentParser(description='BTC Top-Bottom Indicators Scheduler')
    parser.add_argument('--manual', action='store_true', help='Run manual calculation')
    parser.add_argument('--cleanup', type=int, help='Clean up data older than N days')
    parser.add_argument('--status', action='store_true', help='Show system status')

    args = parser.parse_args()

    scheduler = IndicatorScheduler()

    if args.manual:
        success = scheduler.run_manual_calculation()
        sys.exit(0 if success else 1)
    elif args.cleanup:
        scheduler.cleanup_old_data(args.cleanup)
        sys.exit(0)
    elif args.status:
        status = scheduler.get_system_status()
        print(json.dumps(status, indent=2, default=str))
        sys.exit(0)
    else:
        # Run scheduler
        scheduler.run_scheduler()

if __name__ == "__main__":
    main()