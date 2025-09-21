from typing import Optional
import numpy as np
from datetime import datetime, timedelta
from ..base_indicator import BaseIndicator

class PiCycleIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'top')

    def get_indicator_name(self) -> str:
        return 'pi_cycle'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate Pi Cycle Top indicator
        Based on 111-day MA and 350-day MA * 2

        Pi Cycle Top signal occurs when:
        - 111-day MA crosses above 350-day MA * 2
        - Indicates potential cycle top
        """
        try:
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                self.logger.error("Failed to get daily data")
                return None

            prices = daily_data['ohlcv']['close']

            # Pi Cycle Top parameters
            short_period = 111  # 111-day MA
            long_period = 350   # 350-day MA
            multiplier = 2.0    # Pi Cycle multiplier

            if len(prices) < long_period:
                self.logger.warning(f"Insufficient data for Pi Cycle Top (need {long_period}, have {len(prices)})")
                # Use available data with warning
                long_period = min(len(prices) - 1, long_period)
                short_period = min(short_period, long_period // 2)

            if long_period < 100:  # Minimum reasonable period
                self.logger.error("Insufficient data for meaningful Pi Cycle Top calculation")
                return None

            # Calculate moving averages
            ma_111 = prices.rolling(window=short_period).mean()
            ma_350 = prices.rolling(window=long_period).mean()

            if ma_111.isna().iloc[-1] or ma_350.isna().iloc[-1]:
                self.logger.error("MA calculation failed for Pi Cycle Top")
                return None

            # Calculate Pi Cycle Top lines
            signal_line = ma_111      # 111-day MA
            resistance_line = ma_350 * multiplier  # 350-day MA * 2

            current_signal = signal_line.iloc[-1]
            current_resistance = resistance_line.iloc[-1]
            current_price = prices.iloc[-1]

            # Look for crossover signals in recent periods
            lookback = 30
            recent_signal = signal_line.tail(lookback)
            recent_resistance = resistance_line.tail(lookback)

            # Find crossovers (signal line crossing above resistance = top signal)
            crossover_score = 0.0
            days_since_crossover = float('inf')

            for i in range(1, len(recent_signal)):
                prev_signal = recent_signal.iloc[i-1]
                prev_resistance = recent_resistance.iloc[i-1]
                curr_signal = recent_signal.iloc[i]
                curr_resistance = recent_resistance.iloc[i]

                # Bearish crossover (signal crosses above resistance = TOP signal)
                if prev_signal <= prev_resistance and curr_signal > curr_resistance:
                    days_ago = len(recent_signal) - i
                    days_since_crossover = min(days_since_crossover, days_ago)
                    # Weight recent crossovers higher
                    weight = max(0, (lookback - days_ago) / lookback)
                    crossover_score = max(crossover_score, weight * 1.0)

            # Calculate distance metrics
            signal_resistance_ratio = current_signal / current_resistance
            price_signal_ratio = current_price / current_signal

            # Scoring components:
            # 1. Recent crossover signal (60% - high weight due to rarity/importance)
            crossover_component = crossover_score

            # 2. Current positioning (25%)
            # Signal line approaching or above resistance = top setup
            if signal_resistance_ratio >= 1.0:  # Signal above resistance
                position_score = 1.0
            elif signal_resistance_ratio >= 0.98:  # Very close
                position_score = 0.8
            elif signal_resistance_ratio >= 0.95:  # Close
                position_score = 0.6
            else:
                position_score = max(0, (signal_resistance_ratio - 0.90) / 0.05)

            # 3. Price confirmation (15%)
            # Price behavior around signal levels
            if signal_resistance_ratio >= 1.0:  # Top signal active
                if price_signal_ratio >= 1.0:  # Price above signal line
                    confirmation_score = 1.0
                else:
                    confirmation_score = 0.7  # Price below signal but signal above resistance
            else:
                confirmation_score = 0.3  # No active signal

            # Combine components
            final_score = (crossover_component * 0.6 +
                          position_score * 0.25 +
                          confirmation_score * 0.15)

            # Special bonus for very recent crossover (within 5 days)
            if days_since_crossover <= 5:
                final_score *= 1.5
                self.logger.info("RECENT Pi Cycle Top crossover detected!")

            # Ensure [0,1] range
            final_score = max(0, min(1, final_score))

            self.logger.info(f"Pi Cycle Top calculation:")
            self.logger.info(f"  Current price: ${current_price:.2f}")
            self.logger.info(f"  Signal line (111MA): ${current_signal:.2f}")
            self.logger.info(f"  Resistance (350MA*2): ${current_resistance:.2f}")
            self.logger.info(f"  Signal/Resistance ratio: {signal_resistance_ratio:.4f}")
            self.logger.info(f"  Days since crossover: {days_since_crossover}")
            self.logger.info(f"  Components - Crossover: {crossover_component:.4f}, Position: {position_score:.4f}, Confirmation: {confirmation_score:.4f}")
            self.logger.info(f"  Pi Cycle Top score: {final_score:.4f}")

            return float(final_score)

        except Exception as e:
            self.logger.error(f"Error calculating Pi Cycle Top: {e}")
            return None