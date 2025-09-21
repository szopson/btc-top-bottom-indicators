from typing import Optional
import numpy as np
from datetime import datetime, timedelta
from ..base_indicator import BaseIndicator

class PiCycleLowIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return 'pi_cycle_low'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate Pi Cycle Low indicator
        Based on moving averages: 471-day MA and 150-day MA * 0.745

        Pi Cycle Low signal occurs when:
        - 150-day MA * 0.745 crosses above 471-day MA
        - Indicates potential cycle low/bottom
        """
        try:
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                self.logger.error("Failed to get daily data")
                return None

            prices = daily_data['ohlcv']['close']

            # Pi Cycle Low parameters
            long_period = 471   # 471-day MA
            short_period = 150  # 150-day MA
            multiplier = 0.745  # Pi Cycle multiplier

            if len(prices) < long_period:
                self.logger.warning(f"Insufficient data for Pi Cycle Low (need {long_period}, have {len(prices)})")
                # Use available data with warning
                long_period = min(len(prices) - 1, long_period)
                short_period = min(short_period, long_period // 2)

            if long_period < 50:  # Minimum reasonable period
                self.logger.error("Insufficient data for meaningful Pi Cycle Low calculation")
                return None

            # Calculate moving averages
            ma_471 = prices.rolling(window=long_period).mean()
            ma_150 = prices.rolling(window=short_period).mean()

            if ma_471.isna().iloc[-1] or ma_150.isna().iloc[-1]:
                self.logger.error("MA calculation failed for Pi Cycle Low")
                return None

            # Calculate Pi Cycle Low lines
            pi_cycle_line = ma_150 * multiplier  # 150-day MA * 0.745
            support_line = ma_471  # 471-day MA

            current_pi_line = pi_cycle_line.iloc[-1]
            current_support = support_line.iloc[-1]
            current_price = prices.iloc[-1]

            # Look for crossover signals in recent periods
            lookback = 20
            recent_pi = pi_cycle_line.tail(lookback)
            recent_support = support_line.tail(lookback)

            # Find crossovers (Pi line crossing above support = bottom signal)
            crossover_score = 0.0
            days_since_crossover = float('inf')

            for i in range(1, len(recent_pi)):
                prev_pi = recent_pi.iloc[i-1]
                prev_support = recent_support.iloc[i-1]
                curr_pi = recent_pi.iloc[i]
                curr_support = recent_support.iloc[i]

                # Bullish crossover (Pi line crosses above support)
                if prev_pi <= prev_support and curr_pi > curr_support:
                    days_ago = len(recent_pi) - i
                    days_since_crossover = min(days_since_crossover, days_ago)
                    # Weight recent crossovers higher
                    weight = max(0, (lookback - days_ago) / lookback)
                    crossover_score = max(crossover_score, weight * 0.8)

            # Calculate distance metrics
            pi_support_ratio = current_pi / current_support
            price_pi_ratio = current_price / current_pi
            price_support_ratio = current_price / current_support

            # Scoring components:
            # 1. Recent crossover signal (40%)
            crossover_component = crossover_score

            # 2. Current positioning (30%)
            # Pi line above support = bullish setup
            position_score = min(max((pi_support_ratio - 0.995) / 0.01, 0), 1)

            # 3. Price proximity to signals (30%)
            # Price near Pi line during bullish setup = stronger signal
            if pi_support_ratio > 1.0:  # Bullish setup
                if price_pi_ratio >= 0.95 and price_pi_ratio <= 1.05:  # Price near Pi line
                    proximity_score = 1.0
                elif price_support_ratio >= 0.9 and price_support_ratio <= 1.1:  # Price near support
                    proximity_score = 0.7
                else:
                    proximity_score = max(0, 1 - abs(price_pi_ratio - 1) * 2)
            else:
                proximity_score = 0.3  # Bearish setup

            # Combine components
            final_score = (crossover_component * 0.4 +
                          position_score * 0.3 +
                          proximity_score * 0.3)

            # Bonus for very recent crossover
            if days_since_crossover <= 10:
                final_score *= 1.2

            final_score = max(0, min(1, final_score))  # Ensure [0,1] range

            self.logger.info(f"Pi Cycle Low calculation:")
            self.logger.info(f"  Current price: ${current_price:.2f}")
            self.logger.info(f"  Pi line (150MA * 0.745): ${current_pi:.2f}")
            self.logger.info(f"  Support (471MA): ${current_support:.2f}")
            self.logger.info(f"  Pi/Support ratio: {pi_support_ratio:.4f}")
            self.logger.info(f"  Days since crossover: {days_since_crossover}")
            self.logger.info(f"  Components - Crossover: {crossover_component:.4f}, Position: {position_score:.4f}, Proximity: {proximity_score:.4f}")
            self.logger.info(f"  Pi Cycle Low score: {final_score:.4f}")

            return float(final_score)

        except Exception as e:
            self.logger.error(f"Error calculating Pi Cycle Low: {e}")
            return None