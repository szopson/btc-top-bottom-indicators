from typing import Optional
import numpy as np
from ..base_indicator import BaseIndicator

class PuellMultipleIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return 'puell_multiple'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate Puell Multiple
        Puell Multiple = Daily Issuance Value USD / 365-day MA of Daily Issuance Value USD

        Note: This is a simplified implementation using mining revenue proxy
        In production, you'd want actual mining data from on-chain providers
        """
        try:
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                self.logger.error("Failed to get daily data")
                return None

            prices = daily_data['ohlcv']['close']
            volumes = daily_data['ohlcv']['volume']

            if len(prices) < 365:
                self.logger.warning("Insufficient data for full 365-day MA, using available data")
                ma_period = min(len(prices) - 1, 365)
            else:
                ma_period = 365

            if ma_period < 30:  # Minimum reasonable period
                self.logger.error("Insufficient data for Puell Multiple calculation")
                return None

            # Proxy for daily issuance value (simplified approach)
            # In reality, this should be: blocks_mined * block_reward * btc_price
            # For now, using price * volume as a proxy for mining revenue/activity

            # Current Bitcoin mining details (approximate)
            blocks_per_day = 144  # ~144 blocks per day
            current_block_reward = 6.25  # As of 2024 (halves every ~4 years)

            # Calculate daily issuance value proxy
            current_price = prices.iloc[-1]
            daily_issuance_value = blocks_per_day * current_block_reward * current_price

            # Calculate 365-day (or available) moving average of daily issuance values
            historical_issuance_values = []

            for i in range(ma_period):
                hist_price = prices.iloc[-(i + 1)]
                hist_issuance = blocks_per_day * current_block_reward * hist_price
                historical_issuance_values.append(hist_issuance)

            ma_365_issuance = np.mean(historical_issuance_values)

            if ma_365_issuance == 0:
                self.logger.error("Invalid MA calculation for Puell Multiple")
                return None

            # Calculate Puell Multiple
            puell_multiple = daily_issuance_value / ma_365_issuance

            # Additional validation using volume as mining activity proxy
            current_volume = volumes.iloc[-1]
            avg_volume = volumes.tail(ma_period).mean()
            volume_factor = current_volume / avg_volume if avg_volume > 0 else 1.0

            # Adjust Puell Multiple slightly based on volume (mining activity proxy)
            adjusted_puell = puell_multiple * (0.9 + 0.1 * min(volume_factor, 2.0))

            self.logger.info(f"Puell Multiple calculation:")
            self.logger.info(f"  Current price: ${current_price:.2f}")
            self.logger.info(f"  Daily issuance value: ${daily_issuance_value:.0f}")
            self.logger.info(f"  {ma_period}-day MA issuance: ${ma_365_issuance:.0f}")
            self.logger.info(f"  Raw Puell Multiple: {puell_multiple:.4f}")
            self.logger.info(f"  Volume factor: {volume_factor:.4f}")
            self.logger.info(f"  Adjusted Puell Multiple: {adjusted_puell:.4f}")

            # Note about using proxy data
            self.logger.warning("Using simplified proxy for Puell Multiple - replace with actual mining data")

            return float(adjusted_puell)

        except Exception as e:
            self.logger.error(f"Error calculating Puell Multiple: {e}")
            return None