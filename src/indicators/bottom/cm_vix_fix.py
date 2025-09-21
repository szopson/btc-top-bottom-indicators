from typing import Optional
import numpy as np
from ..base_indicator import BaseIndicator

class CMVixFixIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return 'cm_vix_fix'

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate CM VIX Fix - Crypto Market VIX Fix
        VIX Fix = (Highest Close in Period - Low) / Highest Close in Period * 100
        High values indicate oversold/capitulation conditions
        """
        try:
            # Get daily OHLCV data
            daily_data = self.tf_manager.get_daily_data()
            if not daily_data:
                self.logger.error("Failed to get daily data")
                return None

            ohlcv = daily_data['ohlcv']
            if len(ohlcv) < 22:  # Need sufficient data
                self.logger.error("Insufficient OHLCV data")
                return None

            # VIX Fix parameters
            period = 22  # 22-day lookback

            # Get recent data
            recent_data = ohlcv.tail(period)

            # Calculate VIX Fix
            highest_close = recent_data['close'].max()
            current_low = ohlcv['low'].iloc[-1]  # Today's low

            if highest_close == 0:
                self.logger.error("Invalid highest close value")
                return None

            vix_fix = (highest_close - current_low) / highest_close * 100

            # Additional smoothing - take average of last 3 days
            vix_fix_values = []
            for i in range(3):
                if len(ohlcv) > i:
                    period_high = ohlcv['close'].iloc[-(period + i):-(i) if i > 0 else len(ohlcv)].max()
                    period_low = ohlcv['low'].iloc[-(i + 1)]
                    if period_high > 0:
                        vf = (period_high - period_low) / period_high * 100
                        vix_fix_values.append(vf)

            if vix_fix_values:
                vix_fix = np.mean(vix_fix_values)

            self.logger.info(f"CM VIX Fix: {vix_fix:.4f}")
            self.logger.info(f"Highest close ({period}d): ${highest_close:.2f}, Current low: ${current_low:.2f}")

            return float(vix_fix)

        except Exception as e:
            self.logger.error(f"Error calculating CM VIX Fix: {e}")
            return None