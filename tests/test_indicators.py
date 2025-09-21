import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.config.config_manager import ConfigManager
from src.indicators.timeframe_manager import TimeframeManager
from src.data_adapters.tradingview_adapter import TradingViewAdapter

class TestIndicators(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.config = ConfigManager()
        self.tv_adapter = TradingViewAdapter(self.config)
        self.tf_manager = TimeframeManager(self.config, self.tv_adapter)

        # Create mock data
        self.mock_ohlcv = pd.DataFrame({
            'open': np.random.normal(45000, 1000, 100),
            'high': np.random.normal(46000, 1000, 100),
            'low': np.random.normal(44000, 1000, 100),
            'close': np.random.normal(45000, 1000, 100),
            'volume': np.random.normal(100000, 20000, 100)
        })

        self.mock_indicators = {
            'rsi': pd.Series(np.random.uniform(30, 70, 100)),
            'macd': pd.Series(np.random.normal(0, 100, 100)),
            'signal': pd.Series(np.random.normal(0, 100, 100)),
            'histogram': pd.Series(np.random.normal(0, 50, 100))
        }

    @patch('src.indicators.timeframe_manager.TimeframeManager.get_timeframe_data')
    def test_bottom_indicator_calculation(self, mock_get_data):
        """Test bottom indicator calculation"""
        # Mock timeframe data
        mock_get_data.return_value = {
            'ohlcv': self.mock_ohlcv,
            'indicators': self.mock_indicators,
            'timeframe': 'D',
            'symbol': 'BTCUSD'
        }

        # Test Volume Burst 2D indicator
        from src.indicators.bottom.volume_burst_2d import VolumeBurst2DIndicator
        indicator = VolumeBurst2DIndicator(self.config, self.tf_manager)

        raw_value = indicator.calculate_raw_value()
        self.assertIsInstance(raw_value, (int, float, type(None)))

        if raw_value is not None:
            normalized_score = indicator.calculate_normalized_score()
            self.assertIsInstance(normalized_score, (int, float))
            self.assertGreaterEqual(normalized_score, 0)
            self.assertLessEqual(normalized_score, 1)

    @patch('src.indicators.timeframe_manager.TimeframeManager.get_timeframe_data')
    def test_top_indicator_calculation(self, mock_get_data):
        """Test top indicator calculation"""
        # Mock timeframe data
        mock_get_data.return_value = {
            'ohlcv': self.mock_ohlcv,
            'indicators': self.mock_indicators,
            'timeframe': 'D',
            'symbol': 'BTCUSD'
        }

        # Test BBWP indicator
        from src.indicators.top.bbwp import BBWPIndicator

        # Add Bollinger Bands to mock data
        mock_indicators_with_bb = self.mock_indicators.copy()
        mock_indicators_with_bb.update({
            'upper': pd.Series(np.random.uniform(46000, 47000, 100)),
            'lower': pd.Series(np.random.uniform(43000, 44000, 100)),
            'width': pd.Series(np.random.uniform(1000, 3000, 100))
        })

        mock_get_data.return_value['indicators'] = mock_indicators_with_bb

        indicator = BBWPIndicator(self.config, self.tf_manager)

        raw_value = indicator.calculate_raw_value()
        self.assertIsInstance(raw_value, (int, float, type(None)))

        if raw_value is not None:
            normalized_score = indicator.calculate_normalized_score()
            self.assertIsInstance(normalized_score, (int, float))
            self.assertGreaterEqual(normalized_score, 0)
            self.assertLessEqual(normalized_score, 1)

    def test_config_manager(self):
        """Test configuration manager"""
        # Test data sources config
        data_sources = self.config.data_sources
        self.assertIn('bitcoin_magazine_pro', data_sources)
        self.assertIn('ycharts', data_sources)
        self.assertIn('tradingview', data_sources)

        # Test weights config
        weights = self.config.weights
        self.assertIn('bottom_indicators', weights)
        self.assertIn('top_indicators', weights)

        # Test bounds config
        bounds = self.config.bounds
        self.assertIn('bottom_bounds', bounds)
        self.assertIn('top_bounds', bounds)

    def test_normalization(self):
        """Test value normalization"""
        bounds = {'lower': 0, 'upper': 100}

        # Test normal values
        self.assertEqual(self.config.normalize_value(50, bounds), 0.5)
        self.assertEqual(self.config.normalize_value(0, bounds), 0.0)
        self.assertEqual(self.config.normalize_value(100, bounds), 1.0)

        # Test out-of-bounds values
        self.assertEqual(self.config.normalize_value(-10, bounds), 0.0)
        self.assertEqual(self.config.normalize_value(110, bounds), 1.0)

    @patch('src.data_adapters.tradingview_adapter.TradingViewAdapter.get_timeframe_data')
    def test_timeframe_manager(self, mock_get_tf_data):
        """Test timeframe manager functionality"""
        mock_get_tf_data.return_value = {
            'ohlcv': self.mock_ohlcv,
            'indicators': self.mock_indicators,
            'timeframe': 'D',
            'symbol': 'BTCUSD'
        }

        # Test data retrieval
        data = self.tf_manager.get_daily_data()
        self.assertIsNotNone(data)
        self.assertIn('ohlcv', data)
        self.assertIn('indicators', data)

        # Test cache functionality
        data2 = self.tf_manager.get_daily_data()  # Should use cache
        self.assertEqual(data, data2)

        # Test cache status
        cache_status = self.tf_manager.get_cache_status()
        self.assertIsInstance(cache_status, dict)

class TestDataAdapters(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager()

    def test_tradingview_adapter(self):
        """Test TradingView adapter"""
        adapter = TradingViewAdapter(self.config)

        # Test technical indicator calculations
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108])

        # Test RSI calculation
        rsi = adapter.calculate_rsi(prices, period=5)
        self.assertIsInstance(rsi, pd.Series)

        # Test MACD calculation
        macd_data = adapter.calculate_macd(prices)
        self.assertIn('macd', macd_data)
        self.assertIn('signal', macd_data)
        self.assertIn('histogram', macd_data)

    @patch('requests.Session.get')
    def test_bitcoin_magazine_scraper(self, mock_get):
        """Test Bitcoin Magazine scraper"""
        from src.data_adapters.bitcoin_magazine_scraper import BitcoinMagazineScraper

        # Mock HTML response
        mock_response = Mock()
        mock_response.content = b'<html><div class="value">123.45</div></html>'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        scraper = BitcoinMagazineScraper(self.config)

        # Note: This will likely return None in testing due to mock limitations
        # but tests that the method doesn't crash
        result = scraper.get_cvdd()
        self.assertIsInstance(result, (float, type(None)))

class TestComposers(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager()

    @patch('src.composer.bottom_composer.BottomComposer.calculate_individual_scores')
    def test_bottom_composer(self, mock_calc_scores):
        """Test bottom composer"""
        from src.composer.bottom_composer import BottomComposer
        from src.indicators.timeframe_manager import TimeframeManager
        from src.data_adapters.tradingview_adapter import TradingViewAdapter

        tv_adapter = TradingViewAdapter(self.config)
        tf_manager = TimeframeManager(self.config, tv_adapter)
        composer = BottomComposer(self.config, tf_manager)

        # Mock individual scores
        mock_calc_scores.return_value = {
            'test_indicator': {
                'name': 'test_indicator',
                'type': 'bottom',
                'raw_value': 0.5,
                'normalized_score': 0.6,
                'weight': 10,
                'bounds': {'lower': 0, 'upper': 1}
            }
        }

        # Test weighted score calculation
        individual_scores = mock_calc_scores.return_value
        weighted_result = composer.calculate_weighted_score(individual_scores)

        self.assertIn('composite_score', weighted_result)
        self.assertIsInstance(weighted_result['composite_score'], float)

    def test_signal_interpretation(self):
        """Test signal interpretation"""
        from src.composer.bottom_composer import BottomComposer
        from src.indicators.timeframe_manager import TimeframeManager
        from src.data_adapters.tradingview_adapter import TradingViewAdapter

        tv_adapter = TradingViewAdapter(self.config)
        tf_manager = TimeframeManager(self.config, tv_adapter)
        composer = BottomComposer(self.config, tf_manager)

        # Test different score interpretations
        interpretations = [
            composer.generate_bottom_signal_interpretation(0.9),
            composer.generate_bottom_signal_interpretation(0.5),
            composer.generate_bottom_signal_interpretation(0.1)
        ]

        for interp in interpretations:
            self.assertIn('strength', interp)
            self.assertIn('description', interp)
            self.assertIn('score', interp)

if __name__ == '__main__':
    unittest.main()