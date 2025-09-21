# BTC Top-Bottom Indicators

A comprehensive Bitcoin market analysis system that calculates TOP and BOTTOM indicators using multiple timeframes and data sources to identify potential market cycle extremes.

## Overview

This system implements 21 technical indicators (11 for BOTTOM detection, 10 for TOP detection) that are aggregated into composite scores to help identify:

- **BOTTOM signals**: Potential market lows and accumulation opportunities
- **TOP signals**: Potential market highs and distribution phases

## Features

- **Multi-timeframe Analysis**: Monthly (M), Weekly (W), 5-Day, 3-Day, and Daily (D) timeframes
- **Multiple Data Sources**: TradingView, Bitcoin Magazine Pro, YCharts, and on-chain providers
- **Automated Scheduling**: Twice-daily calculations at 08:00 and 20:00 UTC
- **Comprehensive Storage**: SQLite database + JSON/CSV/Excel exports
- **Historical Tracking**: Maintains calculation history for backtesting
- **Web Scraping**: Automated data collection from external sources

## Architecture

```
src/
├── config/              # Configuration management
├── data_adapters/       # Data source integrations
├── indicators/          # Individual indicator implementations
│   ├── bottom/         # 11 bottom indicators
│   ├── top/            # 10 top indicators
│   └── timeframe_manager.py
├── composer/           # Score aggregation system
├── storage/            # Database and file logging
└── scheduler/          # Automated execution
```

## Bottom Indicators (11)

1. **CVDD/Terminal Price Relative** - Valuation extremes
2. **M Timed Bottom Score** - Time-weighted composite
3. **2D Volume Burst** - Short-term volume spikes
4. **CM VIX Fix** - Volatility-based oversold conditions
5. **Gaussian Channel** - Price position vs Gaussian-smoothed channel
6. **3D MMD** - Multi-timeframe momentum descriptor
7. **Hash Ribbons** - Miner capitulation/recovery signals
8. **W Wavefront** - 5-oscillator composite (Stoch RSI, MACD, etc.)
9. **SuperTrend** - ATR-based trend filter
10. **Pi Cycle Low** - Moving average crossover signals
11. **Puell Multiple** - Miner revenue vs historical average

## Top Indicators (10)

1. **CVDD/Terminal Price Relative** - Valuation extremes
2. **M Timed Top Score** - Time-weighted composite
3. **3D Volume** - Multi-horizon volume analysis
4. **BBWP** - Bollinger Band Width Percentile
5. **MMD** - Market momentum deterioration
6. **Funding Rates** - Derivatives sentiment
7. **NUPL** - Net Unrealized Profit/Loss
8. **WaveTrend Oscillator** - Momentum oscillator
9. **Transaction Cost** - Network fee analysis
10. **Pi Cycle** - Moving average top signals

## Data Sources

- **TradingView**: BTCUSD price/volume data and technical indicators
- **Bitcoin Magazine Pro**: CVDD, Terminal Price, NUPL metrics
- **YCharts**: Bitcoin average transaction fees
- **Exchange APIs**: Funding rates from Binance, Bybit, OKEx
- **On-chain Providers**: Hash rate, difficulty, mining data (planned)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd topBottom
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python main.py --status
   ```

## Usage

### Manual Calculation

Run a single calculation:
```bash
python main.py
```

Run with Excel export:
```bash
python main.py --excel
```

### Scheduled Operation

Start the scheduler for twice-daily execution:
```bash
python scheduler/indicator_scheduler.py
```

Run manual calculation via scheduler:
```bash
python scheduler/indicator_scheduler.py --manual
```

### System Management

Show system status:
```bash
python main.py --status
```

Clean up old data:
```bash
python main.py --cleanup 30  # Remove data older than 30 days
```

### Output Formats

The system generates multiple output formats:

1. **JSON**: Complete calculation results with metadata
2. **CSV**: Individual indicators and summary data
3. **Excel**: Comprehensive reports with multiple sheets
4. **SQLite**: Persistent database storage
5. **Historical CSV**: Append-only files for backtesting

## Configuration

Key configuration files in `src/config/`:

- `data_sources.json`: API endpoints and scraping targets
- `weights.json`: Indicator weights for composite scores
- `bounds.json`: Normalization ranges for each indicator

### Customizing Weights

Edit `src/config/weights.json` to adjust indicator importance:

```json
{
  "bottom_indicators": {
    "cvdd_terminal_relative": 12,
    "m_timed_bottom_score": 15,
    "hash_ribbons": 14,
    ...
  }
}
```

### Adjusting Bounds

Edit `src/config/bounds.json` to modify normalization ranges:

```json
{
  "bottom_bounds": {
    "puell_multiple": {"lower": 0.1, "upper": 2.0},
    "cm_vix_fix": {"lower": 0.0, "upper": 100.0},
    ...
  }
}
```

## Score Interpretation

### Bottom Scores (0.0 - 1.0)

- **0.8 - 1.0**: Very Strong bottom signal
- **0.6 - 0.8**: Strong bottom signal
- **0.4 - 0.6**: Moderate bottom signal
- **0.2 - 0.4**: Weak bottom signal
- **0.0 - 0.2**: Very weak bottom signal

### Top Scores (0.0 - 1.0)

- **0.8 - 1.0**: Very Strong top signal
- **0.6 - 0.8**: Strong top signal
- **0.4 - 0.6**: Moderate top signal
- **0.2 - 0.4**: Weak top signal
- **0.0 - 0.2**: Very weak top signal

## Development

### Running Tests

```bash
python -m pytest tests/ -v
```

### Adding New Indicators

1. Create indicator class inheriting from `BaseIndicator`
2. Implement `calculate_raw_value()` and `get_indicator_name()`
3. Add to appropriate composer (bottom/top)
4. Update configuration files with weights and bounds

### Example Indicator Implementation

```python
from ..base_indicator import BaseIndicator

class MyIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'bottom')

    def get_indicator_name(self) -> str:
        return 'my_indicator'

    def calculate_raw_value(self) -> Optional[float]:
        # Your calculation logic here
        return calculated_value
```

## Monitoring and Logging

- **Application logs**: `btc_indicators.log`
- **Scheduler logs**: `scheduler.log`
- **Database**: `btc_indicators.db`
- **Outputs**: `outputs/` directory

## Performance Considerations

- **Data Caching**: Timeframe data is cached for 60 minutes
- **Rate Limiting**: Web scraping includes delays and retry logic
- **Database Cleanup**: Automatic cleanup of old data
- **Error Handling**: Graceful degradation when data sources fail

## Limitations

1. **Sample Data**: TradingView adapter currently uses sample data (replace with real API)
2. **Web Scraping**: Dependent on external website structures
3. **Rate Limits**: Some data sources may impose rate limits
4. **Proxy Data**: Hash Ribbons and Puell Multiple use price-based proxies

## Future Enhancements

- Real TradingView API integration
- Additional on-chain data providers
- Machine learning signal validation
- Real-time WebSocket data feeds
- Advanced backtesting framework
- Web dashboard interface

## License

This project is for educational and research purposes. Ensure compliance with data provider terms of service when using external APIs.

## Disclaimer

This system is for informational purposes only and should not be considered financial advice. Always do your own research before making investment decisions.