from typing import Optional
import numpy as np
from ..base_indicator import BaseIndicator

class SuperTrendIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return 'supertrend'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate SuperTrend indicator score
        SuperTrend trend changes and price distance from SuperTrend line
        """
        try:
            # Get daily data with SuperTrend
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                self.logger.error("Failed to get daily data")
                return None

            # Get SuperTrend from indicators
            if 'supertrend' not in daily_data['indicators']:
                self.logger.error("SuperTrend not available in indicators")
                return None

            supertrend_data = daily_data['indicators']
            supertrend_values = supertrend_data['supertrend']
            trend_direction = supertrend_data['trend']
            current_price = daily_data['ohlcv']['close'].iloc[-1]

            if len(supertrend_values) < 10:
                self.logger.error("Insufficient SuperTrend data")
                return None

            # Current SuperTrend values
            current_supertrend = supertrend_values.iloc[-1]
            current_trend = trend_direction.iloc[-1]

            # Look for trend changes (potential bottom signals)
            recent_trends = trend_direction.tail(5)
            trend_changes = 0
            for i in range(1, len(recent_trends)):
                if recent_trends.iloc[i] != recent_trends.iloc[i-1]:
                    trend_changes += 1

            # Calculate price distance from SuperTrend
            price_distance = abs(current_price - current_supertrend) / current_price * 100

            # For bottom detection:
            # 1. Recent trend change from bearish to bullish (+)
            # 2. Price close to SuperTrend line (+)
            # 3. Currently in bullish trend (+)

            score = 0.0

            # Trend direction component (40% weight)
            if current_trend == 1:  # Bullish trend
                score += 0.4
            elif current_trend == -1:  # Bearish trend
                score += 0.1

            # Trend change component (35% weight)
            if trend_changes > 0:
                # Recent trend change detected
                if recent_trends.iloc[-1] == 1 and recent_trends.iloc[-2] == -1:
                    # Changed from bearish to bullish (strong bottom signal)
                    score += 0.35
                elif trend_changes >= 2:
                    # Multiple trend changes (indecision, moderate signal)
                    score += 0.20

            # Price distance component (25% weight)
            # Closer to SuperTrend = stronger signal
            if price_distance <= 1.0:  # Within 1%
                score += 0.25
            elif price_distance <= 2.0:  # Within 2%
                score += 0.20
            elif price_distance <= 5.0:  # Within 5%
                score += 0.10

            self.logger.info(f"SuperTrend: ${current_supertrend:.2f}, Price: ${current_price:.2f}")
            self.logger.info(f"Trend: {current_trend}, Distance: {price_distance:.2f}%, Changes: {trend_changes}")
            self.logger.info(f"SuperTrend score: {score:.4f}")

            return float(score)

        except Exception as e:
            self.logger.error(f"Error calculating SuperTrend: {e}")
            return None