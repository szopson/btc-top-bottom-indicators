from typing import Optional
import numpy as np
import pandas as pd
from ..base_indicator import BaseIndicator

class WavetrendOscillatorIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'top')

    def get_indicator_name(self) -> str:
        return 'wavetrend_oscillator'

    def calculate_wavetrend(self, prices: pd.Series, channel_length: int = 10, average_length: int = 21) -> Optional[pd.Series]:
        """
        Calculate WaveTrend Oscillator
        Similar to LazyBear's WaveTrend indicator
        """
        try:
            if len(prices) < max(channel_length, average_length) + 10:
                return None

            # Calculate AP (Average Price) - typically HLC3
            # Since we only have close prices, we'll use close
            ap = prices

            # Calculate ESA (Exponential Moving Average of AP)
            esa = ap.ewm(span=channel_length).mean()

            # Calculate absolute difference
            d = (ap - esa).abs()

            # Calculate ESA of the absolute difference
            d_ema = d.ewm(span=channel_length).mean()

            # Calculate CI (Channel Index)
            ci = (ap - esa) / (0.015 * d_ema)

            # Replace infinities and NaNs
            ci = ci.replace([np.inf, -np.inf], np.nan).fillna(0)

            # Calculate TCI (True Channel Index) - EMA of CI
            tci = ci.ewm(span=average_length).mean()

            # WaveTrend oscillates around 0, typically between -100 and +100
            wavetrend = tci

            return wavetrend

        except Exception as e:
            self.logger.error(f"Error calculating WaveTrend: {e}")
            return None

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate WaveTrend Oscillator
        High positive values indicate overbought conditions (potential tops)
        Values typically range from -100 to +100
        """
        try:
            # Get daily price data
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                self.logger.error("Failed to get daily data")
                return None

            prices = daily_data['ohlcv']['close']
            if len(prices) < 50:  # Need sufficient data
                self.logger.error("Insufficient price data for WaveTrend")
                return None

            # Calculate WaveTrend
            wavetrend = self.calculate_wavetrend(prices)

            if wavetrend is None or wavetrend.isna().iloc[-1]:
                self.logger.error("WaveTrend calculation failed")
                return None

            current_wt = wavetrend.iloc[-1]

            # Additional analysis: divergence detection
            recent_wt = wavetrend.tail(10)
            recent_prices = prices.tail(10)

            if len(recent_wt) >= 5:
                # Simple divergence check
                wt_trend = np.polyfit(range(len(recent_wt)), recent_wt, 1)[0]
                price_trend = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]

                # Bearish divergence: price making higher highs, WaveTrend making lower highs
                divergence_factor = 1.0
                if price_trend > 0 and wt_trend < 0:
                    divergence_factor = 1.2  # Boost signal for bearish divergence
                    self.logger.info("Potential bearish divergence detected")

                adjusted_wt = current_wt * divergence_factor

            else:
                adjusted_wt = current_wt

            # Analyze overbought/oversold levels
            if current_wt > 60:
                level = "Overbought"
            elif current_wt > 40:
                level = "Elevated"
            elif current_wt > -40:
                level = "Neutral"
            elif current_wt > -60:
                level = "Oversold"
            else:
                level = "Deeply Oversold"

            self.logger.info(f"WaveTrend Oscillator: {current_wt:.2f} ({level})")
            if 'divergence_factor' in locals():
                self.logger.info(f"Divergence factor: {divergence_factor:.2f}")
                self.logger.info(f"Adjusted WaveTrend: {adjusted_wt:.2f}")

            # Return adjusted value (will be normalized using bounds: -100 to +100)
            return float(adjusted_wt if 'adjusted_wt' in locals() else current_wt)

        except Exception as e:
            self.logger.error(f"Error calculating WaveTrend Oscillator: {e}")
            return None