from typing import Optional, Dict
import numpy as np
from datetime import datetime, time
from ..base_indicator import BaseIndicator

class TimedTopScoreIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'top')

    def get_indicator_name(self) -> str:
        return 'm_timed_top_score'

    def calculate_distribution_component(self) -> Optional[float]:
        """Calculate distribution phase component using monthly timeframe"""
        try:
            monthly_data = self.tf_manager.get_monthly_data()
            if not monthly_data:
                return None

            # Analyze price vs volume for distribution signs
            ohlcv = monthly_data['ohlcv']
            if len(ohlcv) < 10:
                return None

            prices = ohlcv['close']
            volumes = ohlcv['volume']

            # Calculate recent price and volume trends
            recent_periods = 6
            recent_prices = prices.tail(recent_periods)
            recent_volumes = volumes.tail(recent_periods)

            # Price trend
            price_trend = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]

            # Volume trend
            volume_trend = np.polyfit(range(len(recent_volumes)), recent_volumes, 1)[0]

            # Distribution pattern: rising prices with declining volume
            if price_trend > 0 and volume_trend < 0:
                distribution_score = 0.9  # Strong distribution signal
            elif price_trend > 0 and volume_trend > 0:
                distribution_score = 0.4  # Healthy uptrend (less top risk)
            elif price_trend < 0 and volume_trend > 0:
                distribution_score = 0.7  # Price weakness with high volume
            else:
                distribution_score = 0.5  # Neutral

            return distribution_score

        except Exception as e:
            self.logger.error(f"Error calculating distribution component: {e}")
            return None

    def calculate_momentum_exhaustion_component(self) -> Optional[float]:
        """Calculate momentum exhaustion component"""
        try:
            # Get momentum across multiple timeframes
            momentum_daily = self.tf_manager.calculate_momentum('D', periods=14)
            momentum_weekly = self.tf_manager.calculate_momentum('W', periods=4)

            scores = []

            # Daily momentum exhaustion
            if momentum_daily is not None:
                if momentum_daily < -10:  # Negative momentum
                    daily_score = 0.8
                elif momentum_daily < 5:  # Weak momentum
                    daily_score = 0.6
                elif momentum_daily < 15:  # Moderate momentum
                    daily_score = 0.4
                else:  # Strong momentum (less top risk)
                    daily_score = 0.2

                scores.append(('daily', daily_score, momentum_daily))

            # Weekly momentum context
            if momentum_weekly is not None:
                if momentum_weekly < -5:  # Negative weekly momentum
                    weekly_score = 0.9
                elif momentum_weekly < 10:  # Weak weekly momentum
                    weekly_score = 0.6
                else:  # Strong weekly momentum
                    weekly_score = 0.3

                scores.append(('weekly', weekly_score, momentum_weekly))

            if not scores:
                return None

            # Weighted average
            total_score = sum(score for _, score, _ in scores)
            avg_score = total_score / len(scores)

            self.logger.info(f"Momentum exhaustion - Daily: {momentum_daily}, Weekly: {momentum_weekly}")

            return avg_score

        except Exception as e:
            self.logger.error(f"Error calculating momentum exhaustion: {e}")
            return None

    def calculate_sentiment_component(self) -> Optional[float]:
        """Calculate sentiment/euphoria component"""
        try:
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                return None

            # Use RSI as sentiment proxy
            if 'rsi' in daily_data['indicators']:
                rsi = daily_data['indicators']['rsi'].iloc[-1]

                # High RSI indicates overbought/euphoric conditions
                if rsi >= 80:  # Extreme overbought
                    sentiment_score = 1.0
                elif rsi >= 70:  # Overbought
                    sentiment_score = 0.8
                elif rsi >= 60:  # Elevated
                    sentiment_score = 0.6
                elif rsi >= 50:  # Above neutral
                    sentiment_score = 0.4
                else:  # Below neutral
                    sentiment_score = 0.2

                return sentiment_score

            return 0.5  # Neutral if no RSI data

        except Exception as e:
            self.logger.error(f"Error calculating sentiment component: {e}")
            return None

    def calculate_volatility_expansion_component(self) -> Optional[float]:
        """Calculate volatility expansion component"""
        try:
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                return None

            prices = daily_data['ohlcv']['close']
            if len(prices) < 30:
                return None

            # Calculate recent volatility expansion
            recent_returns = prices.pct_change().tail(10).std()
            historical_returns = prices.pct_change().tail(30).std()

            if historical_returns == 0:
                return 0.5

            volatility_ratio = recent_returns / historical_returns

            # At tops, volatility often expands due to uncertainty
            if volatility_ratio >= 2.0:  # High volatility expansion
                vol_score = 0.8
            elif volatility_ratio >= 1.5:  # Moderate expansion
                vol_score = 0.6
            elif volatility_ratio >= 1.2:  # Slight expansion
                vol_score = 0.5
            else:  # Low volatility
                vol_score = 0.3

            return vol_score

        except Exception as e:
            self.logger.error(f"Error calculating volatility expansion: {e}")
            return None

    def calculate_time_weight(self) -> float:
        """Calculate time-based weight factor for top detection"""
        try:
            current_time = datetime.now().time()
            scheduled_times = [time(8, 0), time(20, 0)]  # 08:00 and 20:00

            # Calculate proximity to scheduled times
            current_minutes = current_time.hour * 60 + current_time.minute

            min_distance = float('inf')
            for sched_time in scheduled_times:
                sched_minutes = sched_time.hour * 60 + sched_time.minute
                distance = min(abs(current_minutes - sched_minutes),
                             1440 - abs(current_minutes - sched_minutes))
                min_distance = min(min_distance, distance)

            # For tops, we might want to emphasize certain times
            # Market opens and closes often see distribution activity
            max_distance = 6 * 60  # 6 hours
            time_weight = max(0.7, 1.0 - (min_distance / max_distance) * 0.3)

            return time_weight

        except Exception as e:
            self.logger.error(f"Error calculating time weight: {e}")
            return 1.0

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate M Timed Top Score
        Combines distribution, momentum exhaustion, sentiment, and volatility
        """
        try:
            # Calculate individual components
            distribution_score = self.calculate_distribution_component()
            momentum_score = self.calculate_momentum_exhaustion_component()
            sentiment_score = self.calculate_sentiment_component()
            volatility_score = self.calculate_volatility_expansion_component()

            # Component weights for top detection
            weights = {
                'distribution': 0.3,
                'momentum_exhaustion': 0.3,
                'sentiment': 0.25,
                'volatility': 0.15
            }

            # Calculate weighted score
            total_weight = 0
            weighted_sum = 0

            components = {
                'distribution': distribution_score,
                'momentum_exhaustion': momentum_score,
                'sentiment': sentiment_score,
                'volatility': volatility_score
            }

            for component, score in components.items():
                if score is not None:
                    weight = weights[component]
                    weighted_sum += score * weight
                    total_weight += weight

            if total_weight == 0:
                self.logger.error("No valid components for timed top score")
                return None

            base_score = weighted_sum / total_weight

            # Apply time weighting
            time_weight = self.calculate_time_weight()
            final_score = base_score * time_weight

            self.logger.info(f"Timed Top Score components:")
            self.logger.info(f"  Distribution: {distribution_score:.4f}" if distribution_score else "  Distribution: None")
            self.logger.info(f"  Momentum exhaustion: {momentum_score:.4f}" if momentum_score else "  Momentum exhaustion: None")
            self.logger.info(f"  Sentiment: {sentiment_score:.4f}" if sentiment_score else "  Sentiment: None")
            self.logger.info(f"  Volatility: {volatility_score:.4f}" if volatility_score else "  Volatility: None")
            self.logger.info(f"  Base score: {base_score:.4f}")
            self.logger.info(f"  Time weight: {time_weight:.4f}")
            self.logger.info(f"  Final timed top score: {final_score:.4f}")

            return float(final_score)

        except Exception as e:
            self.logger.error(f"Error calculating M Timed Top Score: {e}")
            return None