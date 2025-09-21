import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

class IndicatorDatabase:
    def __init__(self, db_path: str = "btc_indicators.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.init_database()

    def init_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create calculations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS calculations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        calculation_type TEXT NOT NULL,
                        composite_score REAL,
                        data_quality_score REAL,
                        duration_seconds REAL,
                        raw_data TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create individual indicators table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS indicator_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        calculation_id INTEGER,
                        indicator_name TEXT NOT NULL,
                        indicator_type TEXT NOT NULL,
                        raw_value REAL,
                        normalized_score REAL,
                        weight REAL,
                        bounds_lower REAL,
                        bounds_upper REAL,
                        timestamp TEXT NOT NULL,
                        success BOOLEAN,
                        error_message TEXT,
                        FOREIGN KEY (calculation_id) REFERENCES calculations (id)
                    )
                """)

                # Create data sources status table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS data_sources_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        source_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        response_time_ms REAL,
                        error_message TEXT,
                        data_quality TEXT
                    )
                """)

                # Create system logs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL,
                        component TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT
                    )
                """)

                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_calculations_timestamp ON calculations(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_calculations_type ON calculations(calculation_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_indicators_name ON indicator_results(indicator_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_indicators_type ON indicator_results(indicator_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_sources_timestamp ON data_sources_status(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp)")

                conn.commit()
                self.logger.info("Database initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    def store_calculation(self, results: Dict[str, Any]) -> Optional[int]:
        """Store a complete calculation result"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Extract calculation info
                calc_info = results.get('calculation_info', {})
                timestamp = calc_info.get('start_time', datetime.now()).isoformat()
                duration = calc_info.get('duration_seconds', 0)

                # Store bottom calculation
                bottom_id = None
                if 'bottom_analysis' in results:
                    bottom_analysis = results['bottom_analysis']
                    composite_score = bottom_analysis.get('composite_score')
                    data_quality = bottom_analysis.get('data_quality', {}).get('success_rate', 0)

                    cursor.execute("""
                        INSERT INTO calculations
                        (timestamp, calculation_type, composite_score, data_quality_score, duration_seconds, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (timestamp, 'bottom', composite_score, data_quality, duration, json.dumps(bottom_analysis)))

                    bottom_id = cursor.lastrowid

                    # Store individual bottom indicators
                    if 'individual_indicators' in bottom_analysis:
                        self._store_individual_indicators(cursor, bottom_id, bottom_analysis['individual_indicators'])

                # Store top calculation
                top_id = None
                if 'top_analysis' in results:
                    top_analysis = results['top_analysis']
                    composite_score = top_analysis.get('composite_score')
                    data_quality = top_analysis.get('data_quality', {}).get('success_rate', 0)

                    cursor.execute("""
                        INSERT INTO calculations
                        (timestamp, calculation_type, composite_score, data_quality_score, duration_seconds, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (timestamp, 'top', composite_score, data_quality, duration, json.dumps(top_analysis)))

                    top_id = cursor.lastrowid

                    # Store individual top indicators
                    if 'individual_indicators' in top_analysis:
                        self._store_individual_indicators(cursor, top_id, top_analysis['individual_indicators'])

                conn.commit()
                self.logger.info(f"Stored calculation results - Bottom ID: {bottom_id}, Top ID: {top_id}")
                return bottom_id if bottom_id else top_id

        except Exception as e:
            self.logger.error(f"Error storing calculation: {e}")
            return None

    def _store_individual_indicators(self, cursor, calculation_id: int, indicators: Dict[str, Any]):
        """Store individual indicator results"""
        for indicator_name, result in indicators.items():
            try:
                bounds = result.get('bounds', {})
                timestamp = result.get('timestamp', datetime.now())
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.isoformat()

                cursor.execute("""
                    INSERT INTO indicator_results
                    (calculation_id, indicator_name, indicator_type, raw_value, normalized_score,
                     weight, bounds_lower, bounds_upper, timestamp, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    calculation_id,
                    indicator_name,
                    result.get('type'),
                    result.get('raw_value'),
                    result.get('normalized_score'),
                    result.get('weight'),
                    bounds.get('lower'),
                    bounds.get('upper'),
                    timestamp,
                    result.get('normalized_score') is not None,
                    result.get('error')
                ))

            except Exception as e:
                self.logger.error(f"Error storing indicator {indicator_name}: {e}")

    def get_recent_calculations(self, hours: int = 24, calc_type: str = None) -> List[Dict[str, Any]]:
        """Get recent calculations"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                where_clause = "WHERE datetime(timestamp) > datetime('now', '-{} hours')".format(hours)
                if calc_type:
                    where_clause += f" AND calculation_type = '{calc_type}'"

                cursor.execute(f"""
                    SELECT * FROM calculations
                    {where_clause}
                    ORDER BY timestamp DESC
                """)

                columns = [description[0] for description in cursor.description]
                results = []

                for row in cursor.fetchall():
                    result = dict(zip(columns, row))
                    # Parse raw_data JSON
                    if result['raw_data']:
                        try:
                            result['raw_data'] = json.loads(result['raw_data'])
                        except:
                            pass
                    results.append(result)

                return results

        except Exception as e:
            self.logger.error(f"Error getting recent calculations: {e}")
            return []

    def get_indicator_history(self, indicator_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get historical data for a specific indicator"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM indicator_results
                    WHERE indicator_name = ?
                    AND datetime(timestamp) > datetime('now', '-{} days')
                    ORDER BY timestamp DESC
                """.format(days), (indicator_name,))

                columns = [description[0] for description in cursor.description]
                results = []

                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))

                return results

        except Exception as e:
            self.logger.error(f"Error getting indicator history: {e}")
            return []

    def log_system_event(self, level: str, component: str, message: str, details: Dict[str, Any] = None):
        """Log system events"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO system_logs (timestamp, level, component, message, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    level,
                    component,
                    message,
                    json.dumps(details) if details else None
                ))

                conn.commit()

        except Exception as e:
            self.logger.error(f"Error logging system event: {e}")

    def cleanup_old_data(self, days: int = 90):
        """Clean up old data to manage database size"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Clean old calculations and related indicators
                cursor.execute("""
                    DELETE FROM indicator_results
                    WHERE calculation_id IN (
                        SELECT id FROM calculations
                        WHERE datetime(timestamp) < datetime('now', '-{} days')
                    )
                """.format(days))

                cursor.execute("""
                    DELETE FROM calculations
                    WHERE datetime(timestamp) < datetime('now', '-{} days')
                """.format(days))

                # Clean old logs
                cursor.execute("""
                    DELETE FROM system_logs
                    WHERE datetime(timestamp) < datetime('now', '-{} days')
                """.format(days))

                # Clean old data source status
                cursor.execute("""
                    DELETE FROM data_sources_status
                    WHERE datetime(timestamp) < datetime('now', '-{} days')
                """.format(days))

                conn.commit()
                self.logger.info(f"Cleaned up data older than {days} days")

        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                stats = {}

                # Count records in each table
                tables = ['calculations', 'indicator_results', 'data_sources_status', 'system_logs']
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]

                # Database file size
                db_file = Path(self.db_path)
                if db_file.exists():
                    stats['database_size_mb'] = db_file.stat().st_size / (1024 * 1024)

                # Recent activity
                cursor.execute("""
                    SELECT COUNT(*) FROM calculations
                    WHERE datetime(timestamp) > datetime('now', '-24 hours')
                """)
                stats['calculations_last_24h'] = cursor.fetchone()[0]

                return stats

        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}