from typing import Optional
from ..base_indicator import BaseIndicator
from ...data_adapters.bitcoin_magazine_scraper import BitcoinMagazineScraper

class CVDDTerminalRelativeIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'top')
        self.btc_mag_scraper = BitcoinMagazineScraper(config_manager)

    def get_indicator_name(self) -> str:
        return 'cvdd_terminal_relative'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate relative position of current price between CVDD and Terminal Price
        Formula: (current_price - cvdd) / (terminal_price - cvdd)
        For top indicator: higher relative position = stronger top signal
        """
        try:
            # Get current BTC price
            current_price = self.tf_manager.market_adapter.get_current_price()
            if current_price is None:
                self.logger.error("Failed to get current BTC price")
                return None

            # Get CVDD and Terminal Price from Bitcoin Magazine Pro
            cvdd = self.btc_mag_scraper.get_cvdd()
            terminal_price = self.btc_mag_scraper.get_terminal_price()

            if cvdd is None or terminal_price is None:
                self.logger.error(f"Failed to get CVDD ({cvdd}) or Terminal Price ({terminal_price})")
                return None

            # Calculate relative position
            if terminal_price <= cvdd:
                self.logger.warning(f"Terminal Price ({terminal_price}) <= CVDD ({cvdd}), invalid range")
                return None

            relative_position = (current_price - cvdd) / (terminal_price - cvdd)

            # For top indicator, higher relative position = higher top risk
            self.logger.info(f"Current: ${current_price}, CVDD: ${cvdd}, Terminal: ${terminal_price}")
            self.logger.info(f"Relative position: {relative_position:.4f}")

            return relative_position

        except Exception as e:
            self.logger.error(f"Error calculating CVDD/Terminal relative position: {e}")
            return None