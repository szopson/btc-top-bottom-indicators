from typing import Optional
import numpy as np
from ..base_indicator import BaseIndicator

class MMDIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'top')

    def get_indicator_name(self) -> str:
        return 'mmd'

    def calculate_momentum_breadth(self, timeframe: str, periods: int = 14) -> Optional[float]:
        """Calculate momentum and breadth for given timeframe"""
        try:
            data = self.tf_manager.get_timeframe_data(timeframe)
            if not data:
                return None

            prices = data['ohlcv']['close']
            volumes = data['ohlcv']['volume']

            if len(prices) < periods + 5:
                return None

            # Calculate price momentum
            current_price = prices.iloc[-1]
            past_price = prices.iloc[-(periods + 1)]
            price_momentum = (current_price - past_price) / past_price * 100

            # Calculate volume momentum
            current_volume = volumes.iloc[-1]
            avg_volume = volumes.tail(periods).mean()
            volume_momentum = (current_volume / avg_volume - 1) * 100 if avg_volume > 0 else 0

            # Calculate momentum strength (RSI-like)
            price_changes = prices.pct_change().tail(periods)
            positive_changes = price_changes[price_changes > 0].sum()
            negative_changes = abs(price_changes[price_changes < 0].sum())

            if negative_changes == 0:
                momentum_strength = 100
            else:
                rs = positive_changes / negative_changes
                momentum_strength = 100 - (100 / (1 + rs))

            # Combine metrics
            combined_momentum = (price_momentum * 0.5 +
                               volume_momentum * 0.2 +
                               (momentum_strength - 50) * 0.3)  # Center around 0

            return combined_momentum

        except Exception as e:
            self.logger.error(f"Error calculating momentum breadth for {timeframe}: {e}")
            return None

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate MMD (Market Momentum Descriptor) for TOP
        At tops, momentum typically deteriorates across multiple timeframes
        """
        try:
            # Calculate momentum across multiple timeframes
            timeframes = ['D', 'W', 'M']
            periods = [14, 8, 4]  # Adjusted periods for each timeframe

            momentum_values = []

            for tf, period in zip(timeframes, periods):
                momentum = self.calculate_momentum_breadth(tf, period)
                if momentum is not None:
                    momentum_values.append(momentum)
                    self.logger.info(f"{tf} momentum: {momentum:.4f}")

            if not momentum_values:
                self.logger.error("Failed to calculate momentum for any timeframe")
                return None

            # Weight timeframes (daily most important for tops)
            if len(momentum_values) >= 3:
                weighted_momentum = (momentum_values[0] * 0.6 +  # Daily
                                   momentum_values[1] * 0.3 +    # Weekly
                                   momentum_values[2] * 0.1)     # Monthly
            elif len(momentum_values) == 2:
                weighted_momentum = (momentum_values[0] * 0.7 +
                                   momentum_values[1] * 0.3)
            else:
                weighted_momentum = momentum_values[0]

            # Additional analysis: momentum divergence
            daily_data = self.tf_manager.get_daily_data()
            if daily_data:
                prices = daily_data['ohlcv']['close']
                if len(prices) >= 20:
                    # Check for momentum divergence
                    recent_prices = prices.tail(10)
                    price_trend = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]

                    # If price is rising but momentum is falling = bearish divergence
                    if price_trend > 0 and weighted_momentum < -5:
                        divergence_factor = 1.3  # Boost top signal
                        self.logger.info("Bearish momentum divergence detected")
                    elif price_trend > 0 and weighted_momentum > 20:
                        divergence_factor = 0.8  # Strong momentum, less top risk
                    else:
                        divergence_factor = 1.0

                    adjusted_momentum = weighted_momentum * divergence_factor
                else:
                    adjusted_momentum = weighted_momentum
            else:
                adjusted_momentum = weighted_momentum

            # For top indicator: lower/negative momentum = higher top risk
            # Convert to top risk score (invert momentum)
            if adjusted_momentum > 20:
                top_score = 0.5  # Strong momentum = low top risk
            elif adjusted_momentum > 0:
                top_score = 1.0 + (20 - adjusted_momentum) / 40  # Moderate momentum
            elif adjusted_momentum > -20:
                top_score = 2.0 + abs(adjusted_momentum) / 20    # Weak momentum
            else:
                top_score = 4.0  # Very weak momentum = high top risk

            # Cap the score
            final_score = min(top_score, 5.0)

            self.logger.info(f"MMD Analysis:")
            self.logger.info(f"  Momentum values: {momentum_values}")
            self.logger.info(f"  Weighted momentum: {weighted_momentum:.4f}")
            if 'divergence_factor' in locals():
                self.logger.info(f"  Divergence factor: {divergence_factor:.2f}")
                self.logger.info(f"  Adjusted momentum: {adjusted_momentum:.4f}")
            self.logger.info(f"  Final MMD score: {final_score:.4f}")

            return float(final_score)

        except Exception as e:
            self.logger.error(f"Error calculating MMD: {e}")
            return None