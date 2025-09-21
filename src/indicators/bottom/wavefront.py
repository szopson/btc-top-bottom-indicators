from typing import Optional, Dict
import numpy as np
from ..base_indicator import BaseIndicator

class WavefrontIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return 'w_wavefront'

    def calculate_stochastic_rsi(self, timeframe: str, period: int = 14) -> Optional[float]:
        """Calculate Stochastic RSI for given timeframe"""
        try:
            data = self.tf_manager.get_timeframe_data(timeframe)
            if not data or 'rsi' not in data['indicators']:
                return None

            rsi_values = data['indicators']['rsi'].dropna()
            if len(rsi_values) < period:
                return None

            # Get recent RSI values
            recent_rsi = rsi_values.tail(period)
            current_rsi = rsi_values.iloc[-1]

            # Calculate Stochastic of RSI
            rsi_min = recent_rsi.min()
            rsi_max = recent_rsi.max()

            if rsi_max == rsi_min:
                return 0.5  # Neutral

            stoch_rsi = (current_rsi - rsi_min) / (rsi_max - rsi_min)
            return stoch_rsi

        except Exception as e:
            self.logger.error(f"Error calculating Stochastic RSI for {timeframe}: {e}")
            return None

    def calculate_snabbel_rsi_ema(self, timeframe: str) -> Optional[float]:
        """Calculate Snabbel RSI EMA (custom RSI with EMA smoothing)"""
        try:
            data = self.tf_manager.get_timeframe_data(timeframe)
            if not data or 'rsi' not in data['indicators']:
                return None

            rsi_values = data['indicators']['rsi'].dropna()
            if len(rsi_values) < 10:
                return None

            # Apply EMA smoothing to RSI
            ema_smoothed = rsi_values.ewm(span=9).mean()
            current_value = ema_smoothed.iloc[-1]

            # Normalize to [0,1] range
            normalized = current_value / 100.0
            return normalized

        except Exception as e:
            self.logger.error(f"Error calculating Snabbel RSI EMA for {timeframe}: {e}")
            return None

    def calculate_tdi_gm(self, timeframe: str) -> Optional[float]:
        """Calculate TDI (Traders Dynamic Index) Green Mean"""
        try:
            data = self.tf_manager.get_timeframe_data(timeframe)
            if not data or 'rsi' not in data['indicators']:
                return None

            rsi_values = data['indicators']['rsi'].dropna()
            if len(rsi_values) < 20:
                return None

            # TDI Green Mean is typically a smoothed RSI
            # Using double smoothing: EMA of EMA
            first_smooth = rsi_values.ewm(span=13).mean()
            second_smooth = first_smooth.ewm(span=8).mean()

            current_value = second_smooth.iloc[-1]
            normalized = current_value / 100.0
            return normalized

        except Exception as e:
            self.logger.error(f"Error calculating TDI GM for {timeframe}: {e}")
            return None

    def calculate_accumulation_distribution(self, timeframe: str) -> Optional[float]:
        """Calculate Accumulation/Distribution Line"""
        try:
            data = self.tf_manager.get_timeframe_data(timeframe)
            if not data:
                return None

            ohlcv = data['ohlcv']
            if len(ohlcv) < 20:
                return None

            # A/D Line calculation
            high = ohlcv['high']
            low = ohlcv['low']
            close = ohlcv['close']
            volume = ohlcv['volume']

            # Money Flow Multiplier
            clv = ((close - low) - (high - close)) / (high - low)
            clv = clv.fillna(0)  # Handle division by zero

            # Money Flow Volume
            mfv = clv * volume

            # Accumulation/Distribution Line
            ad_line = mfv.cumsum()

            # Get rate of change for recent period
            if len(ad_line) >= 10:
                current_ad = ad_line.iloc[-1]
                past_ad = ad_line.iloc[-10]
                ad_change = (current_ad - past_ad) / abs(past_ad) if past_ad != 0 else 0

                # Normalize to roughly [-1, 1] range
                normalized = np.tanh(ad_change / 10.0)  # Adjust scaling as needed
                return (normalized + 1) / 2  # Convert to [0, 1]

            return 0.5

        except Exception as e:
            self.logger.error(f"Error calculating A/D for {timeframe}: {e}")
            return None

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate W Wavefront - combination of 5 oscillators
        1. M Stochastic RSI
        2. M Snabbel_RSI_EMA
        3. 10D MACD
        4. M TDI GM
        5. M Accumulation/Distribution
        """
        try:
            # Get component weights from config
            wavefront_weights = self.config.weights.get('wavefront_components', {
                'm_stochastic_rsi': 0.2,
                'm_snabbel_rsi_ema': 0.2,
                '10d_macd': 0.2,
                'm_tdi_gm': 0.2,
                'm_accumulation_distribution': 0.2
            })

            components = {}

            # 1. Monthly Stochastic RSI
            stoch_rsi = self.calculate_stochastic_rsi('M')
            if stoch_rsi is not None:
                components['m_stochastic_rsi'] = stoch_rsi

            # 2. Monthly Snabbel RSI EMA
            snabbel_rsi = self.calculate_snabbel_rsi_ema('M')
            if snabbel_rsi is not None:
                components['m_snabbel_rsi_ema'] = snabbel_rsi

            # 3. 10D MACD (using daily data, 10-period MACD)
            daily_data = self.tf_manager.get_daily_data()
            if daily_data and 'macd' in daily_data['indicators']:
                macd_hist = daily_data['indicators']['histogram']
                if len(macd_hist) > 0:
                    # Normalize MACD histogram
                    current_hist = macd_hist.iloc[-1]
                    recent_hist = macd_hist.tail(20)
                    if len(recent_hist) > 0:
                        hist_std = recent_hist.std()
                        if hist_std > 0:
                            normalized_macd = np.tanh(current_hist / hist_std)
                            components['10d_macd'] = (normalized_macd + 1) / 2

            # 4. Monthly TDI GM
            tdi_gm = self.calculate_tdi_gm('M')
            if tdi_gm is not None:
                components['m_tdi_gm'] = tdi_gm

            # 5. Monthly Accumulation/Distribution
            ad_value = self.calculate_accumulation_distribution('M')
            if ad_value is not None:
                components['m_accumulation_distribution'] = ad_value

            if not components:
                self.logger.error("No wavefront components calculated successfully")
                return None

            # Calculate weighted average
            total_weight = 0
            weighted_sum = 0

            for component, value in components.items():
                weight = wavefront_weights.get(component, 0.2)
                weighted_sum += value * weight
                total_weight += weight

            if total_weight == 0:
                return None

            wavefront_score = weighted_sum / total_weight

            self.logger.info(f"Wavefront components: {components}")
            self.logger.info(f"Wavefront score: {wavefront_score:.4f}")

            return float(wavefront_score)

        except Exception as e:
            self.logger.error(f"Error calculating W Wavefront: {e}")
            return None