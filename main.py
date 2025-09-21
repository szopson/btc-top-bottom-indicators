#!/usr/bin/env python3
"""
BTC Top-Bottom Indicators - Main Entry Point

This script provides the main interface for running the BTC Top-Bottom indicators system.
It supports manual calculations, scheduled runs, and system management.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.config.config_manager import ConfigManager
from src.composer.main_composer import MainComposer
from src.storage.database import IndicatorDatabase
from src.storage.file_logger import FileLogger

def setup_logging(level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('btc_indicators.log'),
            logging.StreamHandler()
        ]
    )

def run_calculation(export_excel=False):
    """Run a single calculation"""
    try:
        print("Initializing BTC Top-Bottom Indicators...")

        # Initialize components
        config = ConfigManager()
        composer = MainComposer(config)
        database = IndicatorDatabase()
        file_logger = FileLogger()

        print("Running indicators calculation...")

        # Run calculation
        results = composer.calculate_both_indicators(refresh_data=True)

        if 'error' in results:
            print(f"❌ Calculation failed: {results['error']}")
            return False

        # Display results
        print("\n" + "="*60)
        print("📊 CALCULATION RESULTS")
        print("="*60)

        # Bottom results
        if 'bottom_analysis' in results:
            bottom = results['bottom_analysis']
            if bottom.get('composite_score') is not None:
                interpretation = bottom.get('interpretation', {})
                print(f"📉 BOTTOM Score: {bottom['composite_score']:.4f}")
                print(f"   Strength: {interpretation.get('strength', 'Unknown')}")
                print(f"   Signal: {interpretation.get('description', 'No description')}")
            else:
                print("📉 BOTTOM: Calculation failed")

        # Top results
        if 'top_analysis' in results:
            top = results['top_analysis']
            if top.get('composite_score') is not None:
                interpretation = top.get('interpretation', {})
                print(f"📈 TOP Score: {top['composite_score']:.4f}")
                print(f"   Strength: {interpretation.get('strength', 'Unknown')}")
                print(f"   Signal: {interpretation.get('description', 'No description')}")
            else:
                print("📈 TOP: Calculation failed")

        # Market context
        if 'market_context' in results and 'current_btc_price' in results['market_context']:
            price = results['market_context']['current_btc_price']
            if price:
                print(f"💰 Current BTC Price: ${price:,.2f}")

        # Performance info
        calc_info = results.get('calculation_info', {})
        duration = calc_info.get('duration_seconds', 0)
        print(f"⏱️  Calculation completed in {duration:.2f} seconds")

        print("="*60)

        # Store results
        print("\n💾 Storing results...")

        # Database storage
        calculation_id = database.store_calculation(results)
        if calculation_id:
            print(f"✅ Stored in database (ID: {calculation_id})")

        # JSON export
        json_file = file_logger.log_calculation_json(results)
        if json_file:
            print(f"✅ Exported to JSON: {json_file}")

        # CSV export
        csv_timestamp = file_logger.log_calculation_csv(results)
        if csv_timestamp:
            print(f"✅ Exported to CSV files (timestamp: {csv_timestamp})")

        # Excel export (optional)
        if export_excel:
            excel_file = file_logger.create_excel_report(results)
            if excel_file:
                print(f"✅ Excel report created: {excel_file}")

        # Append to historical data
        file_logger.append_to_historical_csv(results)
        print("✅ Appended to historical data")

        print("\n🎉 Calculation completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        logging.exception("Error in calculation")
        return False

def show_system_status():
    """Show system status"""
    try:
        config = ConfigManager()
        composer = MainComposer(config)
        database = IndicatorDatabase()

        print("\n" + "="*50)
        print("📋 SYSTEM STATUS")
        print("="*50)

        # Database stats
        db_stats = database.get_database_stats()
        print("📊 Database:")
        for key, value in db_stats.items():
            print(f"   {key.replace('_', ' ').title()}: {value}")

        # Cache status
        cache_status = composer.tf_manager.get_cache_status()
        print("\n🗂️  Data Cache:")
        for timeframe, status in cache_status.items():
            valid = "✅" if status['valid'] else "❌"
            print(f"   {timeframe}: {valid} (Age: {status.get('age_minutes', 'N/A')} min)")

        # Recent calculations
        recent_calcs = database.get_recent_calculations(hours=24)
        print(f"\n📈 Recent Calculations (24h): {len(recent_calcs)}")

        print("="*50)

    except Exception as e:
        print(f"❌ Error getting system status: {e}")

def cleanup_old_data(days=90):
    """Clean up old data"""
    try:
        database = IndicatorDatabase()
        print(f"🧹 Cleaning up data older than {days} days...")
        database.cleanup_old_data(days)
        print("✅ Cleanup completed")
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='BTC Top-Bottom Indicators System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run single calculation
  python main.py --excel           # Run calculation with Excel export
  python main.py --status          # Show system status
  python main.py --cleanup 30      # Clean data older than 30 days
  python main.py --verbose         # Run with verbose logging
        """
    )

    parser.add_argument('--excel', action='store_true',
                       help='Export results to Excel format')
    parser.add_argument('--status', action='store_true',
                       help='Show system status')
    parser.add_argument('--cleanup', type=int, metavar='DAYS',
                       help='Clean up data older than N days')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)

    try:
        if args.status:
            show_system_status()
        elif args.cleanup:
            cleanup_old_data(args.cleanup)
        else:
            # Run calculation
            success = run_calculation(export_excel=args.excel)
            sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.exception("Unexpected error")
        sys.exit(1)

if __name__ == "__main__":
    main()