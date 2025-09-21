from typing import Optional
import numpy as np
from ..base_indicator import BaseIndicator

class BBWPIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'top')

    def get_indicator_name(self) -> str:
        return 'bbwp'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate BBWP (Bollinger Band Width Percentile)
        Measures current BB width relative to historical BB widths
        High BBWP can indicate high volatility periods (potential tops during uptrends)
        """
        try:
            # Get daily data with Bollinger Bands
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                self.logger.error("Failed to get daily data")
                return None

            # Check if Bollinger Bands are available
            bb_indicators = ['upper', 'lower', 'width']
            for indicator in bb_indicators:
                if indicator not in daily_data['indicators']:
                    self.logger.error(f"Bollinger Band {indicator} not available")
                    return None

            bb_width = daily_data['indicators']['width']

            if len(bb_width) < 100:  # Need sufficient historical data
                self.logger.warning("Insufficient data for BBWP calculation")
                # Use available data
                lookback_period = max(20, len(bb_width) - 1)
            else:
                lookback_period = 100  # Standard BBWP lookback

            if len(bb_width) < lookback_period:
                self.logger.error("Insufficient data for meaningful BBWP calculation")
                return None

            # Get current BB width and historical widths
            current_width = bb_width.iloc[-1]
            historical_widths = bb_width.tail(lookback_period)

            # Calculate percentile of current width relative to historical
            percentile = (historical_widths < current_width).sum() / len(historical_widths) * 100

            # Additional context: trend analysis
            prices = daily_data['ohlcv']['close']
            if len(prices) >= 20:
                # Check if we're in an uptrend (for top detection context)
                sma_20 = prices.rolling(window=20).mean()
                current_price = prices.iloc[-1]
                current_sma = sma_20.iloc[-1]

                trend_context = "uptrend" if current_price > current_sma else "downtrend"

                # In uptrends, high BBWP (>80) can signal exhaustion/top
                # In downtrends, high BBWP can signal capitulation
                if trend_context == "uptrend" and percentile > 80:
                    trend_multiplier = 1.2  # Boost signal in uptrend
                elif trend_context == "downtrend" and percentile > 80:
                    trend_multiplier = 0.8  # Reduce signal in downtrend
                else:
                    trend_multiplier = 1.0

                adjusted_percentile = min(100, percentile * trend_multiplier)

                self.logger.info(f"BBWP calculation:")
                self.logger.info(f"  Current BB width: {current_width:.6f}")
                self.logger.info(f"  Historical percentile: {percentile:.2f}%")
                self.logger.info(f"  Trend context: {trend_context}")
                self.logger.info(f"  Adjusted percentile: {adjusted_percentile:.2f}%")

                return float(adjusted_percentile)

            else:
                self.logger.info(f"BBWP: {percentile:.2f}% (no trend context)")
                return float(percentile)

        except Exception as e:
            self.logger.error(f"Error calculating BBWP: {e}")
            return None