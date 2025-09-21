from typing import Optional
import numpy as np
import pandas as pd
from scipy import stats
from ..base_indicator import BaseIndicator

class GaussianChannelIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return 'gaussian_channel'

    def gaussian_moving_average(self, prices: pd.Series, period: int = 14, sigma: float = 1.0) -> pd.Series:
        """Calculate Gaussian Moving Average"""
        weights = []
        for i in range(period):
            weight = stats.norm.pdf(i, loc=period/2, scale=sigma)
            weights.append(weight)

        # Normalize weights
        weights = np.array(weights)
        weights = weights / weights.sum()

        # Apply convolution
        gma = prices.rolling(window=period).apply(
            lambda x: np.sum(x * weights), raw=True
        )
        return gma

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate position relative to Gaussian Channel
        Distance = (Price - GMA) / Gaussian_STD
        Negative values indicate oversold conditions (good for bottom detection)
        """
        try:
            # Get daily price data
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                self.logger.error("Failed to get daily data")
                return None

            prices = daily_data['ohlcv']['close']
            if len(prices) < 30:  # Need sufficient data
                self.logger.error("Insufficient price data")
                return None

            # Gaussian Channel parameters
            period = 20
            sigma = 2.0

            # Calculate Gaussian Moving Average
            gma = self.gaussian_moving_average(prices, period, sigma)

            # Calculate Gaussian Standard Deviation
            gaussian_std = prices.rolling(window=period).apply(
                lambda x: np.std(x), raw=True
            )

            if gma.isna().iloc[-1] or gaussian_std.iloc[-1] == 0:
                self.logger.error("Invalid GMA or STD calculation")
                return None

            # Current price position relative to channel
            current_price = prices.iloc[-1]
            current_gma = gma.iloc[-1]
            current_std = gaussian_std.iloc[-1]

            # Distance in standard deviations
            distance = (current_price - current_gma) / current_std

            self.logger.info(f"Price: ${current_price:.2f}, GMA: ${current_gma:.2f}, STD: ${current_std:.2f}")
            self.logger.info(f"Gaussian Channel distance: {distance:.4f} standard deviations")

            # For bottom indicator: negative distance (below GMA) = stronger bottom signal
            # We'll return the raw distance and let normalization handle the scoring
            return float(distance)

        except Exception as e:
            self.logger.error(f"Error calculating Gaussian Channel: {e}")
            return None