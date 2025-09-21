from typing import Optional
from ..base_indicator import BaseIndicator
from ...data_adapters.bitcoin_magazine_scraper import BitcoinMagazineScraper

class NUPLIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'top')
        self.btc_mag_scraper = BitcoinMagazineScraper(config_manager)

    def get_indicator_name(self) -> str:
        return 'nupl'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate NUPL (Net Unrealized Profit/Loss) indicator
        High NUPL values indicate market euphoria and potential top risk
        """
        try:
            # Get NUPL from Bitcoin Magazine Pro
            nupl_value = self.btc_mag_scraper.get_nupl()

            if nupl_value is None:
                self.logger.error("Failed to get NUPL value")
                return None

            self.logger.info(f"NUPL value: {nupl_value:.4f}")

            # NUPL is already in percentage form, return as-is
            # Normalization will be handled by bounds (Upper: 66.8, Lower: -32.67)
            return float(nupl_value)

        except Exception as e:
            self.logger.error(f"Error calculating NUPL: {e}")
            return None