from typing import Optional
from ..base_indicator import BaseIndicator
from ...data_adapters.ycharts_scraper import YChartsScraper

class TransactionCostIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'top')
        self.ycharts_scraper = YChartsScraper(config_manager)

    def get_indicator_name(self) -> str:
        return 'transaction_cost'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate transaction cost indicator
        High transaction fees typically occur during market euphoria/tops
        """
        try:
            # Get Bitcoin average transaction fee from YCharts
            tx_fee = self.ycharts_scraper.get_bitcoin_average_transaction_fee()

            if tx_fee is None:
                self.logger.error("Failed to get transaction fee")
                return None

            self.logger.info(f"Bitcoin average transaction fee: ${tx_fee:.4f}")

            # Return raw fee value (will be normalized using bounds)
            return float(tx_fee)

        except Exception as e:
            self.logger.error(f"Error calculating transaction cost: {e}")
            return None