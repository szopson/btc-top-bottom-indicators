from typing import Optional
import numpy as np
from ..base_indicator import BaseIndicator

class VolumeBurst2DIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return '2d_volume_burst'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate 2-day volume burst using z-score
        High volume during downtrend can indicate capitulation/bottom
        """
        try:
            # Get daily volume data
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                self.logger.error("Failed to get daily data")
                return None

            volume_series = daily_data['ohlcv']['volume']
            if len(volume_series) < 22:  # Need at least 20 for lookback + 2 current
                self.logger.error("Insufficient volume data")
                return None

            # Calculate 2-day average volume
            current_2d_avg = volume_series.tail(2).mean()

            # Calculate z-score against 20-day lookback
            lookback_period = 20
            historical_volume = volume_series.iloc[-(lookback_period + 2):-2]  # Exclude current 2 days

            mean_volume = historical_volume.mean()
            std_volume = historical_volume.std()

            if std_volume == 0:
                self.logger.warning("Zero volume standard deviation")
                return 0.0

            # Z-score of current 2-day average vs historical
            z_score = (current_2d_avg - mean_volume) / std_volume

            self.logger.info(f"2D avg volume: {current_2d_avg:.0f}, Historical avg: {mean_volume:.0f}")
            self.logger.info(f"Volume z-score: {z_score:.4f}")

            # Return z-score (will be normalized using bounds)
            return float(z_score)

        except Exception as e:
            self.logger.error(f"Error calculating 2D volume burst: {e}")
            return None