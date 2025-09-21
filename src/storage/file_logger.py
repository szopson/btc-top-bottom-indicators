import json
import csv
import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import pandas as pd

class FileLogger:
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)

        # Create subdirectories
        (self.output_dir / "json").mkdir(exist_ok=True)
        (self.output_dir / "csv").mkdir(exist_ok=True)
        (self.output_dir / "logs").mkdir(exist_ok=True)

    def log_calculation_json(self, results: Dict[str, Any], filename: str = None) -> str:
        """Log calculation results to JSON file"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"btc_indicators_{timestamp}.json"

            filepath = self.output_dir / "json" / filename

            # Prepare data for JSON serialization
            json_data = self._prepare_for_json(results)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Results logged to {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"Error logging JSON: {e}")
            return None

    def log_calculation_csv(self, results: Dict[str, Any]) -> str:
        """Log calculation results to CSV files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Log bottom indicators to CSV
            if 'bottom_analysis' in results and 'individual_indicators' in results['bottom_analysis']:
                bottom_file = self.output_dir / "csv" / f"bottom_indicators_{timestamp}.csv"
                self._write_indicators_csv(results['bottom_analysis']['individual_indicators'], bottom_file)

            # Log top indicators to CSV
            if 'top_analysis' in results and 'individual_indicators' in results['top_analysis']:
                top_file = self.output_dir / "csv" / f"top_indicators_{timestamp}.csv"
                self._write_indicators_csv(results['top_analysis']['individual_indicators'], top_file)

            # Log summary CSV
            summary_file = self.output_dir / "csv" / f"summary_{timestamp}.csv"
            self._write_summary_csv(results, summary_file)

            self.logger.info(f"CSV files logged with timestamp {timestamp}")
            return timestamp

        except Exception as e:
            self.logger.error(f"Error logging CSV: {e}")
            return None

    def _write_indicators_csv(self, indicators: Dict[str, Any], filepath: Path):
        """Write individual indicators to CSV"""
        try:
            fieldnames = [
                'indicator_name', 'indicator_type', 'raw_value', 'normalized_score',
                'weight', 'bounds_lower', 'bounds_upper', 'timestamp', 'success'
            ]

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for name, data in indicators.items():
                    bounds = data.get('bounds', {})
                    row = {
                        'indicator_name': name,
                        'indicator_type': data.get('type'),
                        'raw_value': data.get('raw_value'),
                        'normalized_score': data.get('normalized_score'),
                        'weight': data.get('weight'),
                        'bounds_lower': bounds.get('lower'),
                        'bounds_upper': bounds.get('upper'),
                        'timestamp': data.get('timestamp'),
                        'success': data.get('normalized_score') is not None
                    }
                    writer.writerow(row)

        except Exception as e:
            self.logger.error(f"Error writing indicators CSV: {e}")

    def _write_summary_csv(self, results: Dict[str, Any], filepath: Path):
        """Write summary data to CSV"""
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow(['Metric', 'Value'])

                # Calculation info
                calc_info = results.get('calculation_info', {})
                writer.writerow(['Calculation Start', calc_info.get('start_time')])
                writer.writerow(['Calculation Duration (s)', calc_info.get('duration_seconds')])

                # Market context
                market_context = results.get('market_context', {})
                writer.writerow(['Current BTC Price', market_context.get('current_btc_price')])

                # Bottom analysis
                if 'bottom_analysis' in results:
                    bottom = results['bottom_analysis']
                    writer.writerow(['Bottom Composite Score', bottom.get('composite_score')])

                    interpretation = bottom.get('interpretation', {})
                    writer.writerow(['Bottom Signal Strength', interpretation.get('strength')])
                    writer.writerow(['Bottom Signal Description', interpretation.get('description')])

                    data_quality = bottom.get('data_quality', {})
                    writer.writerow(['Bottom Success Rate (%)', data_quality.get('success_rate')])

                # Top analysis
                if 'top_analysis' in results:
                    top = results['top_analysis']
                    writer.writerow(['Top Composite Score', top.get('composite_score')])

                    interpretation = top.get('interpretation', {})
                    writer.writerow(['Top Signal Strength', interpretation.get('strength')])
                    writer.writerow(['Top Signal Description', interpretation.get('description')])

                    data_quality = top.get('data_quality', {})
                    writer.writerow(['Top Success Rate (%)', data_quality.get('success_rate')])

        except Exception as e:
            self.logger.error(f"Error writing summary CSV: {e}")

    def append_to_historical_csv(self, results: Dict[str, Any]):
        """Append results to historical CSV files for backtesting"""
        try:
            timestamp = datetime.now()

            # Historical bottom data
            if 'bottom_analysis' in results:
                bottom_csv = self.output_dir / "csv" / "historical_bottom.csv"
                self._append_historical_data(results['bottom_analysis'], bottom_csv, 'bottom', timestamp)

            # Historical top data
            if 'top_analysis' in results:
                top_csv = self.output_dir / "csv" / "historical_top.csv"
                self._append_historical_data(results['top_analysis'], top_csv, 'top', timestamp)

            self.logger.info("Appended to historical CSV files")

        except Exception as e:
            self.logger.error(f"Error appending to historical CSV: {e}")

    def _append_historical_data(self, analysis: Dict[str, Any], filepath: Path, analysis_type: str, timestamp: datetime):
        """Append analysis data to historical CSV"""
        try:
            # Check if file exists to determine if we need headers
            file_exists = filepath.exists()

            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                fieldnames = ['timestamp', 'composite_score', 'signal_strength', 'success_rate']

                # Add individual indicator scores
                if 'individual_indicators' in analysis:
                    for indicator_name in analysis['individual_indicators'].keys():
                        fieldnames.append(f"{indicator_name}_score")

                writer = csv.DictWriter(f, fieldnames=fieldnames)

                # Write header if new file
                if not file_exists:
                    writer.writeheader()

                # Prepare row data
                row = {
                    'timestamp': timestamp.isoformat(),
                    'composite_score': analysis.get('composite_score'),
                    'signal_strength': analysis.get('interpretation', {}).get('strength'),
                    'success_rate': analysis.get('data_quality', {}).get('success_rate')
                }

                # Add individual indicator scores
                if 'individual_indicators' in analysis:
                    for name, data in analysis['individual_indicators'].items():
                        row[f"{name}_score"] = data.get('normalized_score')

                writer.writerow(row)

        except Exception as e:
            self.logger.error(f"Error appending historical data: {e}")

    def create_excel_report(self, results: Dict[str, Any]) -> str:
        """Create comprehensive Excel report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.output_dir / f"btc_indicators_report_{timestamp}.xlsx"

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Summary sheet
                self._create_summary_sheet(results, writer)

                # Bottom indicators sheet
                if 'bottom_analysis' in results:
                    self._create_indicators_sheet(results['bottom_analysis'], writer, 'Bottom Indicators')

                # Top indicators sheet
                if 'top_analysis' in results:
                    self._create_indicators_sheet(results['top_analysis'], writer, 'Top Indicators')

                # Market context sheet
                if 'market_context' in results:
                    self._create_market_context_sheet(results['market_context'], writer)

            self.logger.info(f"Excel report created: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"Error creating Excel report: {e}")
            return None

    def _create_summary_sheet(self, results: Dict[str, Any], writer):
        """Create summary sheet for Excel report"""
        summary_data = []

        # Add calculation info
        calc_info = results.get('calculation_info', {})
        summary_data.append(['Calculation Start', calc_info.get('start_time')])
        summary_data.append(['Duration (seconds)', calc_info.get('duration_seconds')])

        # Add scores
        if 'bottom_analysis' in results:
            bottom = results['bottom_analysis']
            summary_data.append(['Bottom Score', bottom.get('composite_score')])
            summary_data.append(['Bottom Strength', bottom.get('interpretation', {}).get('strength')])

        if 'top_analysis' in results:
            top = results['top_analysis']
            summary_data.append(['Top Score', top.get('composite_score')])
            summary_data.append(['Top Strength', top.get('interpretation', {}).get('strength')])

        df = pd.DataFrame(summary_data, columns=['Metric', 'Value'])
        df.to_excel(writer, sheet_name='Summary', index=False)

    def _create_indicators_sheet(self, analysis: Dict[str, Any], writer, sheet_name: str):
        """Create indicators sheet for Excel report"""
        if 'individual_indicators' not in analysis:
            return

        indicators_data = []
        for name, data in analysis['individual_indicators'].items():
            bounds = data.get('bounds', {})
            indicators_data.append({
                'Indicator': name,
                'Raw Value': data.get('raw_value'),
                'Normalized Score': data.get('normalized_score'),
                'Weight': data.get('weight'),
                'Lower Bound': bounds.get('lower'),
                'Upper Bound': bounds.get('upper'),
                'Success': 'Yes' if data.get('normalized_score') is not None else 'No'
            })

        df = pd.DataFrame(indicators_data)
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    def _create_market_context_sheet(self, market_context: Dict[str, Any], writer):
        """Create market context sheet for Excel report"""
        context_data = []
        for key, value in market_context.items():
            if key != 'data_timestamp':
                context_data.append([key.replace('_', ' ').title(), value])

        df = pd.DataFrame(context_data, columns=['Metric', 'Value'])
        df.to_excel(writer, sheet_name='Market Context', index=False)

    def _prepare_for_json(self, obj: Any) -> Any:
        """Prepare object for JSON serialization"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._prepare_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_for_json(item) for item in obj]
        elif pd.isna(obj):
            return None
        else:
            return obj