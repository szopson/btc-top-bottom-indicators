import logging
import json
from typing import Dict, Any
from datetime import datetime
from ..config.config_manager import ConfigManager
from ..indicators.timeframe_manager import TimeframeManager
from ..data_adapters.real_market_adapter import RealMarketAdapter
from .bottom_composer import BottomComposer
from .top_composer import TopComposer

class MainComposer:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)

        # Initialize data adapters
        self.market_adapter = RealMarketAdapter(config_manager)
        self.tf_manager = TimeframeManager(config_manager, self.market_adapter)

        # Initialize composers
        self.bottom_composer = BottomComposer(config_manager, self.tf_manager)
        self.top_composer = TopComposer(config_manager, self.tf_manager)

    def refresh_data(self) -> bool:
        """Refresh all timeframe data"""
        try:
            self.logger.info("Refreshing market data...")
            success = self.tf_manager.refresh_all_data()
            if success:
                self.logger.info("Market data refreshed successfully")
            else:
                self.logger.warning("Market data refresh encountered issues")
            return success
        except Exception as e:
            self.logger.error(f"Error refreshing market data: {e}")
            return False

    def calculate_both_indicators(self, refresh_data: bool = True) -> Dict[str, Any]:
        """Calculate both TOP and BOTTOM indicators"""
        calculation_start = datetime.now()

        try:
            # Refresh data if requested
            if refresh_data:
                data_success = self.refresh_data()
                if not data_success:
                    self.logger.warning("Data refresh failed, proceeding with cached data")

            # Calculate bottom analysis
            self.logger.info("="*50)
            self.logger.info("CALCULATING BOTTOM INDICATORS")
            self.logger.info("="*50)
            bottom_analysis = self.bottom_composer.calculate_complete_bottom_analysis()

            # Calculate top analysis
            self.logger.info("="*50)
            self.logger.info("CALCULATING TOP INDICATORS")
            self.logger.info("="*50)
            top_analysis = self.top_composer.calculate_complete_top_analysis()

            calculation_end = datetime.now()
            calculation_duration = (calculation_end - calculation_start).total_seconds()

            # Combine results
            combined_results = {
                'calculation_info': {
                    'start_time': calculation_start,
                    'end_time': calculation_end,
                    'duration_seconds': calculation_duration,
                    'data_refreshed': refresh_data
                },
                'bottom_analysis': bottom_analysis,
                'top_analysis': top_analysis,
                'market_context': self._get_market_context(),
                'cache_status': self.tf_manager.get_cache_status()
            }

            # Log summary
            self._log_analysis_summary(combined_results)

            return combined_results

        except Exception as e:
            self.logger.error(f"Error in main calculation: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(),
                'calculation_info': {
                    'start_time': calculation_start,
                    'end_time': datetime.now(),
                    'duration_seconds': (datetime.now() - calculation_start).total_seconds(),
                    'data_refreshed': refresh_data
                }
            }

    def _get_market_context(self) -> Dict[str, Any]:
        """Get current market context"""
        try:
            current_price = self.market_adapter.get_current_price()
            price_stats = self.tf_manager.get_price_statistics('D', periods=30)
            volume_stats = self.tf_manager.get_volume_statistics('D', periods=30)

            context = {
                'current_btc_price': current_price,
                'price_statistics': price_stats,
                'volume_statistics': volume_stats,
                'data_timestamp': datetime.now()
            }

            return context

        except Exception as e:
            self.logger.error(f"Error getting market context: {e}")
            return {'error': str(e)}

    def _log_analysis_summary(self, results: Dict[str, Any]) -> None:
        """Log a summary of the analysis results"""
        try:
            self.logger.info("="*60)
            self.logger.info("ANALYSIS SUMMARY")
            self.logger.info("="*60)

            # Bottom summary
            if 'bottom_analysis' in results and 'composite_score' in results['bottom_analysis']:
                bottom_score = results['bottom_analysis']['composite_score']
                bottom_interpretation = results['bottom_analysis'].get('interpretation', {})
                if bottom_score is not None:
                    self.logger.info(f"BOTTOM Score: {bottom_score:.4f} ({bottom_interpretation.get('strength', 'N/A')})")
                    self.logger.info(f"BOTTOM Signal: {bottom_interpretation.get('description', 'N/A')}")

            # Top summary
            if 'top_analysis' in results and 'composite_score' in results['top_analysis']:
                top_score = results['top_analysis']['composite_score']
                top_interpretation = results['top_analysis'].get('interpretation', {})
                if top_score is not None:
                    self.logger.info(f"TOP Score: {top_score:.4f} ({top_interpretation.get('strength', 'N/A')})")
                    self.logger.info(f"TOP Signal: {top_interpretation.get('description', 'N/A')}")

            # Market context
            if 'market_context' in results and 'current_btc_price' in results['market_context']:
                price = results['market_context']['current_btc_price']
                if price:
                    self.logger.info(f"Current BTC Price: ${price:,.2f}")

            # Performance summary
            if 'calculation_info' in results:
                duration = results['calculation_info']['duration_seconds']
                self.logger.info(f"Calculation completed in {duration:.2f} seconds")

            self.logger.info("="*60)

        except Exception as e:
            self.logger.error(f"Error logging summary: {e}")

    def export_to_json(self, results: Dict[str, Any], filename: str = None) -> str:
        """Export results to JSON file"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"btc_indicators_{timestamp}.json"

            # Convert datetime objects to ISO format for JSON serialization
            json_results = self._prepare_for_json(results)

            with open(filename, 'w') as f:
                json.dump(json_results, f, indent=2, default=str)

            self.logger.info(f"Results exported to {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"Error exporting to JSON: {e}")
            return None

    def _prepare_for_json(self, obj: Any) -> Any:
        """Prepare object for JSON serialization"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._prepare_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_for_json(item) for item in obj]
        else:
            return obj