from typing import Optional, Dict
import numpy as np
from ..base_indicator import BaseIndicator

class MMD3DIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return '3d_mmd'

    def calculate_momentum_descriptor(self, timeframe: str, periods: int = 14) -> Optional[float]:
        """Calculate momentum descriptor for a specific timeframe"""
        try:
            data = self.tf_manager.get_timeframe_data(timeframe)
            if not data:
                return None

            prices = data['ohlcv']['close']
            if len(prices) < periods + 1:
                return None

            # Calculate momentum (rate of change)
            current_price = prices.iloc[-1]
            past_price = prices.iloc[-(periods + 1)]
            momentum = (current_price - past_price) / past_price * 100

            # Calculate momentum z-score
            recent_prices = prices.tail(periods * 2)
            if len(recent_prices) >= periods:
                momentum_values = []
                for i in range(periods, len(recent_prices)):
                    mom = (recent_prices.iloc[i] - recent_prices.iloc[i - periods]) / recent_prices.iloc[i - periods] * 100
                    momentum_values.append(mom)

                if momentum_values:
                    momentum_mean = np.mean(momentum_values)
                    momentum_std = np.std(momentum_values)
                    if momentum_std > 0:
                        momentum_z = (momentum - momentum_mean) / momentum_std
                        return momentum_z

            return 0.0

        except Exception as e:
            self.logger.error(f"Error calculating momentum for {timeframe}: {e}")
            return None

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate 3D Market Momentum Descriptor
        Combines momentum across multiple market segments/timeframes
        For crypto: BTC, ETH, and broader market momentum
        """
        try:
            # Get 3-day timeframe data for main calculation
            momentum_3d = self.calculate_momentum_descriptor('3D', periods=10)

            # Get daily momentum for broader context
            momentum_daily = self.calculate_momentum_descriptor('D', periods=14)

            # Get weekly momentum for trend context
            momentum_weekly = self.calculate_momentum_descriptor('W', periods=4)

            if momentum_3d is None:
                self.logger.error("Failed to calculate 3D momentum")
                return None

            # Combine momentum signals with weights
            # 3D momentum is primary, daily and weekly provide context
            weights = {
                '3d': 0.6,
                'daily': 0.3,
                'weekly': 0.1
            }

            combined_momentum = momentum_3d * weights['3d']

            if momentum_daily is not None:
                combined_momentum += momentum_daily * weights['daily']

            if momentum_weekly is not None:
                combined_momentum += momentum_weekly * weights['weekly']

            # Additional volume confirmation
            volume_stats = self.tf_manager.get_volume_statistics('3D', periods=20)
            if volume_stats:
                volume_factor = min(volume_stats['z_score'] / 2.0, 1.0)  # Cap at 1.0
                combined_momentum *= (1 + volume_factor * 0.2)  # Up to 20% boost

            self.logger.info(f"3D MMD - 3D: {momentum_3d:.4f}, Daily: {momentum_daily}, Weekly: {momentum_weekly}")
            self.logger.info(f"Combined 3D MMD: {combined_momentum:.4f}")

            return float(combined_momentum)

        except Exception as e:
            self.logger.error(f"Error calculating 3D MMD: {e}")
            return None