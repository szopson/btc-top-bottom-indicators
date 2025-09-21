import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from ..data_adapters.real_market_adapter import RealMarketAdapter
from ..config.config_manager import ConfigManager

class TimeframeManager:
    def __init__(self, config_manager: ConfigManager, market_adapter: RealMarketAdapter):
        self.config = config_manager
        self.market_adapter = market_adapter
        self.logger = logging.getLogger(__name__)
        self._data_cache = {}
        self._last_update = {}

    def _is_cache_valid(self, timeframe: str, max_age_minutes: int = 60) -> bool:
        """Check if cached data is still valid"""
        if timeframe not in self._last_update:
            return False

        age = datetime.now() - self._last_update[timeframe]
        return age.total_seconds() / 60 < max_age_minutes

    def get_timeframe_data(self, timeframe: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get data for specific timeframe with caching"""
        if not force_refresh and self._is_cache_valid(timeframe):
            self.logger.info(f"Using cached data for {timeframe}")
            return self._data_cache.get(timeframe)

        self.logger.info(f"Fetching fresh data for {timeframe}")
        data = self.market_adapter.get_timeframe_data(timeframe)

        if data:
            self._data_cache[timeframe] = data
            self._last_update[timeframe] = datetime.now()
            return data

        return None

    def get_monthly_data(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get monthly timeframe data"""
        return self.get_timeframe_data('M', force_refresh)

    def get_weekly_data(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get weekly timeframe data"""
        return self.get_timeframe_data('W', force_refresh)

    def get_5day_data(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get 5-day timeframe data"""
        return self.get_timeframe_data('5D', force_refresh)

    def get_3day_data(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get 3-day timeframe data"""
        return self.get_timeframe_data('3D', force_refresh)

    def get_daily_data(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get daily timeframe data"""
        return self.get_timeframe_data('D', force_refresh)

    def get_all_timeframes(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get data for all timeframes"""
        timeframes = ['M', 'W', '5D', '3D', 'D']
        all_data = {}

        for tf in timeframes:
            data = self.get_timeframe_data(tf, force_refresh)
            if data:
                all_data[tf] = data
            else:
                self.logger.warning(f"Failed to get data for timeframe {tf}")

        return all_data

    def extract_indicator_value(self, timeframe: str, indicator_name: str, lookback: int = 0) -> Optional[float]:
        """Extract specific indicator value from timeframe data"""
        data = self.get_timeframe_data(timeframe)
        if not data:
            return None

        try:
            indicators = data['indicators']
            if indicator_name in indicators:
                series = indicators[indicator_name]
                if isinstance(series, pd.Series) and len(series) > lookback:
                    return float(series.iloc[-(lookback + 1)])
        except Exception as e:
            self.logger.error(f"Error extracting {indicator_name} from {timeframe}: {e}")

        return None

    def extract_ohlcv_value(self, timeframe: str, column: str, lookback: int = 0) -> Optional[float]:
        """Extract OHLCV value from timeframe data"""
        data = self.get_timeframe_data(timeframe)
        if not data:
            return None

        try:
            ohlcv = data['ohlcv']
            if column in ohlcv.columns and len(ohlcv) > lookback:
                return float(ohlcv[column].iloc[-(lookback + 1)])
        except Exception as e:
            self.logger.error(f"Error extracting {column} from {timeframe}: {e}")

        return None

    def get_volume_statistics(self, timeframe: str, periods: int = 20) -> Optional[Dict[str, float]]:
        """Get volume statistics for timeframe"""
        data = self.get_timeframe_data(timeframe)
        if not data:
            return None

        try:
            volume = data['ohlcv']['volume']
            recent_volume = volume.tail(periods)

            return {
                'current': float(volume.iloc[-1]),
                'mean': float(recent_volume.mean()),
                'std': float(recent_volume.std()),
                'z_score': float((volume.iloc[-1] - recent_volume.mean()) / recent_volume.std()),
                'percentile': float((volume.iloc[-1] > recent_volume).sum() / len(recent_volume) * 100)
            }
        except Exception as e:
            self.logger.error(f"Error calculating volume statistics for {timeframe}: {e}")
            return None

    def get_price_statistics(self, timeframe: str, periods: int = 20) -> Optional[Dict[str, float]]:
        """Get price statistics for timeframe"""
        data = self.get_timeframe_data(timeframe)
        if not data:
            return None

        try:
            ohlcv = data['ohlcv']
            recent_closes = ohlcv['close'].tail(periods)
            current_price = float(ohlcv['close'].iloc[-1])

            return {
                'current': current_price,
                'mean': float(recent_closes.mean()),
                'std': float(recent_closes.std()),
                'high': float(ohlcv['high'].tail(periods).max()),
                'low': float(ohlcv['low'].tail(periods).min()),
                'change_pct': float((current_price - recent_closes.iloc[0]) / recent_closes.iloc[0] * 100)
            }
        except Exception as e:
            self.logger.error(f"Error calculating price statistics for {timeframe}: {e}")
            return None

    def calculate_momentum(self, timeframe: str, periods: int = 14) -> Optional[float]:
        """Calculate momentum for timeframe"""
        data = self.get_timeframe_data(timeframe)
        if not data:
            return None

        try:
            closes = data['ohlcv']['close']
            if len(closes) > periods:
                current = closes.iloc[-1]
                past = closes.iloc[-(periods + 1)]
                momentum = (current - past) / past * 100
                return float(momentum)
        except Exception as e:
            self.logger.error(f"Error calculating momentum for {timeframe}: {e}")

        return None

    def refresh_all_data(self) -> bool:
        """Refresh all timeframe data"""
        try:
            self.logger.info("Refreshing all timeframe data...")
            self.get_all_timeframes(force_refresh=True)
            self.logger.info("All timeframe data refreshed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error refreshing all data: {e}")
            return False

    def get_cache_status(self) -> Dict[str, Any]:
        """Get status of cached data"""
        status = {}
        for tf in ['M', 'W', '5D', '3D', 'D']:
            if tf in self._last_update:
                age_minutes = (datetime.now() - self._last_update[tf]).total_seconds() / 60
                status[tf] = {
                    'cached': True,
                    'last_update': self._last_update[tf],
                    'age_minutes': age_minutes,
                    'valid': self._is_cache_valid(tf)
                }
            else:
                status[tf] = {
                    'cached': False,
                    'last_update': None,
                    'age_minutes': None,
                    'valid': False
                }
        return status