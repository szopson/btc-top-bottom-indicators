from typing import Optional
import numpy as np
from ..base_indicator import BaseIndicator

class HashRibbonsIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return 'hash_ribbons'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate Hash Ribbons indicator
        Based on hash rate moving averages - indicates miner capitulation and recovery

        Note: This is a simplified implementation using price-based proxy
        In production, you'd want actual hash rate data from on-chain providers
        """
        try:
            # For now, using price momentum as a proxy for hash rate trends
            # In production, replace with actual hash rate data from Glassnode/CoinMetrics

            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                self.logger.error("Failed to get daily data")
                return None

            prices = daily_data['ohlcv']['close']
            if len(prices) < 60:  # Need sufficient data for MAs
                self.logger.error("Insufficient data for Hash Ribbons")
                return None

            # Hash Ribbons typically use 30-day and 60-day MAs of hash rate
            # Using price MAs as proxy (replace with actual hash rate data)
            short_ma_period = 30
            long_ma_period = 60

            short_ma = prices.rolling(window=short_ma_period).mean()
            long_ma = prices.rolling(window=long_ma_period).mean()

            if short_ma.isna().iloc[-1] or long_ma.isna().iloc[-1]:
                self.logger.error("MA calculation failed")
                return None

            current_short = short_ma.iloc[-1]
            current_long = long_ma.iloc[-1]

            # Hash Ribbons signals:
            # Capitulation: Short MA < Long MA (bearish for miners)
            # Recovery: Short MA crosses above Long MA

            # Calculate the ratio and trend
            ma_ratio = current_short / current_long

            # Look for recent crossover
            lookback = 10
            recent_short = short_ma.tail(lookback)
            recent_long = long_ma.tail(lookback)

            # Find crossovers in recent period
            crossover_score = 0.0

            for i in range(1, len(recent_short)):
                prev_short = recent_short.iloc[i-1]
                prev_long = recent_long.iloc[i-1]
                curr_short = recent_short.iloc[i]
                curr_long = recent_long.iloc[i]

                # Bullish crossover (recovery signal)
                if prev_short <= prev_long and curr_short > curr_long:
                    # Weight recent crossovers higher
                    weight = (len(recent_short) - i) / len(recent_short)
                    crossover_score += weight * 0.8

                # Bearish crossover (capitulation signal) - negative for recovery
                elif prev_short >= prev_long and curr_short < curr_long:
                    weight = (len(recent_short) - i) / len(recent_short)
                    crossover_score -= weight * 0.3

            # Calculate momentum of the ratio
            if len(short_ma) >= 5:
                ratio_current = current_short / current_long
                ratio_past = short_ma.iloc[-5] / long_ma.iloc[-5]
                ratio_momentum = (ratio_current - ratio_past) / ratio_past

                # Positive momentum when short MA is gaining on long MA
                momentum_score = np.tanh(ratio_momentum * 10) * 0.5  # Scale and bound

            else:
                momentum_score = 0.0

            # Combine signals
            # Base score from current ratio (above 1.0 = bullish)
            ratio_score = min(max((ma_ratio - 0.98) / 0.04, 0), 1)  # Normalize around 1.0

            final_score = (ratio_score * 0.4 +
                          (crossover_score + 0.5) * 0.4 +  # Normalize crossover to [0,1]
                          (momentum_score + 0.5) * 0.2)  # Normalize momentum to [0,1]

            final_score = max(0, min(1, final_score))  # Ensure [0,1] range

            self.logger.info(f"Hash Ribbons - Short MA: {current_short:.2f}, Long MA: {current_long:.2f}")
            self.logger.info(f"Ratio: {ma_ratio:.4f}, Crossover: {crossover_score:.4f}, Momentum: {momentum_score:.4f}")
            self.logger.info(f"Hash Ribbons score: {final_score:.4f}")

            # Note: In production, log warning about using price proxy
            self.logger.warning("Using price MA proxy for Hash Ribbons - replace with actual hash rate data")

            return float(final_score)

        except Exception as e:
            self.logger.error(f"Error calculating Hash Ribbons: {e}")
            return None