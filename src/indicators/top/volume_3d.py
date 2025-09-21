from typing import Optional
import numpy as np
from ..base_indicator import BaseIndicator

class Volume3DIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'top')

    def get_indicator_name(self) -> str:
        return '3d_volume'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate 3D Volume indicator
        Multi-horizon volume analysis for distribution/exhaustion detection
        High volume during uptrends can indicate distribution (top signals)
        """
        try:
            # Get volume data from multiple timeframes
            timeframes = ['3D', 'D', 'W']
            volume_scores = []

            for tf in timeframes:
                tf_data = self.tf_manager.get_timeframe_data(tf)
                if tf_data is None:
                    continue

                volume_series = tf_data['ohlcv']['volume']
                if len(volume_series) < 20:
                    continue

                # Calculate volume z-score for this timeframe
                current_volume = volume_series.iloc[-1]
                recent_volume = volume_series.tail(20)

                mean_volume = recent_volume.mean()
                std_volume = recent_volume.std()

                if std_volume > 0:
                    z_score = (current_volume - mean_volume) / std_volume

                    # For tops: high volume during uptrends is bearish
                    # Check price trend for context
                    prices = tf_data['ohlcv']['close']
                    if len(prices) >= 10:
                        price_change = (prices.iloc[-1] - prices.iloc[-10]) / prices.iloc[-10]

                        # If price is rising and volume is high, it's a top signal
                        if price_change > 0 and z_score > 1.5:
                            # High volume in uptrend = distribution signal
                            volume_score = min(z_score / 2.0, 4.0)
                        elif price_change > 0 and z_score > 0.5:
                            # Moderate volume in uptrend
                            volume_score = z_score
                        elif price_change < 0 and z_score > 2.0:
                            # High volume in downtrend = continuation (bearish)
                            volume_score = min(z_score / 1.5, 3.0)
                        else:
                            # Normal volume patterns
                            volume_score = max(0, z_score / 2.0)
                    else:
                        volume_score = max(0, z_score / 2.0)

                    volume_scores.append(volume_score)

            if not volume_scores:
                self.logger.error("Failed to calculate volume scores for any timeframe")
                return None

            # Weight different timeframes
            if len(volume_scores) >= 3:  # All timeframes available
                weighted_score = (volume_scores[0] * 0.5 +  # 3D primary
                                volume_scores[1] * 0.3 +    # Daily secondary
                                volume_scores[2] * 0.2)     # Weekly context
            elif len(volume_scores) == 2:
                weighted_score = (volume_scores[0] * 0.7 + volume_scores[1] * 0.3)
            else:
                weighted_score = volume_scores[0]

            # Get additional volume confirmation from volume ratio
            daily_data = self.tf_manager.get_daily_data()
            if daily_data:
                volume_stats = self.tf_manager.get_volume_statistics('D', periods=30)
                if volume_stats:
                    volume_percentile = volume_stats['percentile']

                    # High volume percentile during uptrend = top risk
                    if volume_percentile > 80:
                        weighted_score *= 1.3
                    elif volume_percentile > 60:
                        weighted_score *= 1.1

            # Cap the final score
            final_score = min(weighted_score, 4.0)

            self.logger.info(f"3D Volume Analysis:")
            self.logger.info(f"  Volume scores by timeframe: {volume_scores}")
            self.logger.info(f"  Weighted score: {weighted_score:.4f}")
            self.logger.info(f"  Final 3D volume score: {final_score:.4f}")

            return float(final_score)

        except Exception as e:
            self.logger.error(f"Error calculating 3D Volume: {e}")
            return None