from typing import Optional, Dict
import numpy as np
from datetime import datetime, time
from ..base_indicator import BaseIndicator

class TimedBottomScoreIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return 'm_timed_bottom_score'

    def calculate_momentum_component(self) -> Optional[float]:
        """Calculate momentum component using monthly timeframe"""
        try:
            monthly_data = self.tf_manager.get_monthly_data()
            if not monthly_data:
                return None

            # Calculate multi-period momentum
            momentum = self.tf_manager.calculate_momentum('M', periods=3)
            if momentum is None:
                return None

            # Normalize momentum (negative momentum = stronger bottom signal)
            # Convert to [0,1] where low values = stronger bottom
            momentum_score = np.tanh(-momentum / 20.0)  # Negative momentum gives positive score
            normalized_momentum = (momentum_score + 1) / 2

            return normalized_momentum

        except Exception as e:
            self.logger.error(f"Error calculating momentum component: {e}")
            return None

    def calculate_volatility_component(self) -> Optional[float]:
        """Calculate volatility component"""
        try:
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                return None

            prices = daily_data['ohlcv']['close']
            if len(prices) < 30:
                return None

            # Calculate recent volatility vs historical
            recent_returns = prices.pct_change().tail(10).std()
            historical_returns = prices.pct_change().tail(30).std()

            if historical_returns == 0:
                return 0.5

            volatility_ratio = recent_returns / historical_returns

            # High volatility can indicate capitulation (good for bottom detection)
            # But extremely high volatility might indicate continued instability
            if volatility_ratio <= 1.5:  # Normal to slightly elevated
                vol_score = volatility_ratio / 1.5
            elif volatility_ratio <= 3.0:  # High volatility (capitulation zone)
                vol_score = 1.0
            else:  # Extremely high volatility
                vol_score = max(0.5, 1.0 - (volatility_ratio - 3.0) / 5.0)

            return vol_score

        except Exception as e:
            self.logger.error(f"Error calculating volatility component: {e}")
            return None

    def calculate_volume_component(self) -> Optional[float]:
        """Calculate volume component"""
        try:
            volume_stats = self.tf_manager.get_volume_statistics('D', periods=20)
            if not volume_stats:
                return None

            # High volume during potential bottoms can indicate capitulation
            volume_z = volume_stats['z_score']

            # Convert z-score to bottom signal strength
            if volume_z >= 2.0:  # Very high volume
                volume_score = 1.0
            elif volume_z >= 1.0:  # High volume
                volume_score = 0.8
            elif volume_z >= 0:  # Above average volume
                volume_score = 0.6
            else:  # Below average volume
                volume_score = max(0.2, 0.6 + volume_z * 0.2)

            return volume_score

        except Exception as e:
            self.logger.error(f"Error calculating volume component: {e}")
            return None

    def calculate_onchain_component(self) -> Optional[float]:
        """Calculate on-chain component (simplified)"""
        try:
            # This would ideally use actual on-chain metrics
            # For now, using price-based proxies

            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                return None

            # Use RSI as proxy for on-chain sentiment
            if 'rsi' in daily_data['indicators']:
                rsi = daily_data['indicators']['rsi'].iloc[-1]
                # Low RSI = oversold = good for bottom detection
                if rsi <= 30:  # Oversold
                    onchain_score = 1.0
                elif rsi <= 40:  # Approaching oversold
                    onchain_score = 0.8
                elif rsi <= 50:  # Below neutral
                    onchain_score = 0.6
                else:  # Above neutral
                    onchain_score = max(0.2, (100 - rsi) / 50)

                return onchain_score

            return 0.5  # Neutral if no data

        except Exception as e:
            self.logger.error(f"Error calculating on-chain component: {e}")
            return None

    def calculate_time_weight(self) -> float:
        """Calculate time-based weight factor"""
        try:
            current_time = datetime.now().time()
            scheduled_times = [time(8, 0), time(20, 0)]  # 08:00 and 20:00

            # Calculate proximity to scheduled times
            current_minutes = current_time.hour * 60 + current_time.minute

            min_distance = float('inf')
            for sched_time in scheduled_times:
                sched_minutes = sched_time.hour * 60 + sched_time.minute
                distance = min(abs(current_minutes - sched_minutes),
                             1440 - abs(current_minutes - sched_minutes))  # Handle day wrap
                min_distance = min(min_distance, distance)

            # Weight is higher closer to scheduled times
            # Maximum weight at scheduled time, minimum weight at 6 hours away
            max_distance = 6 * 60  # 6 hours in minutes
            time_weight = max(0.5, 1.0 - (min_distance / max_distance) * 0.5)

            return time_weight

        except Exception as e:
            self.logger.error(f"Error calculating time weight: {e}")
            return 1.0

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate M Timed Bottom Score
        Combines multiple components with time-based weighting
        """
        try:
            # Calculate individual components
            momentum_score = self.calculate_momentum_component()
            volatility_score = self.calculate_volatility_component()
            volume_score = self.calculate_volume_component()
            onchain_score = self.calculate_onchain_component()

            # Component weights
            weights = {
                'momentum': 0.35,
                'volatility': 0.25,
                'volume': 0.25,
                'onchain': 0.15
            }

            # Calculate weighted score
            total_weight = 0
            weighted_sum = 0

            components = {
                'momentum': momentum_score,
                'volatility': volatility_score,
                'volume': volume_score,
                'onchain': onchain_score
            }

            for component, score in components.items():
                if score is not None:
                    weight = weights[component]
                    weighted_sum += score * weight
                    total_weight += weight

            if total_weight == 0:
                self.logger.error("No valid components for timed bottom score")
                return None

            base_score = weighted_sum / total_weight

            # Apply time weighting
            time_weight = self.calculate_time_weight()
            final_score = base_score * time_weight

            self.logger.info(f"Timed Bottom Score components:")
            self.logger.info(f"  Momentum: {momentum_score:.4f}" if momentum_score else "  Momentum: None")
            self.logger.info(f"  Volatility: {volatility_score:.4f}" if volatility_score else "  Volatility: None")
            self.logger.info(f"  Volume: {volume_score:.4f}" if volume_score else "  Volume: None")
            self.logger.info(f"  On-chain: {onchain_score:.4f}" if onchain_score else "  On-chain: None")
            self.logger.info(f"  Base score: {base_score:.4f}")
            self.logger.info(f"  Time weight: {time_weight:.4f}")
            self.logger.info(f"  Final timed score: {final_score:.4f}")

            return float(final_score)

        except Exception as e:
            self.logger.error(f"Error calculating M Timed Bottom Score: {e}")
            return None