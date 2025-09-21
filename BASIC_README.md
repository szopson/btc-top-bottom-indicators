# BTC Top-Bottom Indicators - Quick Start Guide

## What This System Does

This is a Bitcoin market analysis system that calculates **TOP** and **BOTTOM** signals to help identify potential market cycle extremes. It combines 21 technical indicators into two composite scores (0.0 to 1.0) that indicate:

- **BOTTOM Score**: How likely the current market is at a bottom (buying opportunity)
- **TOP Score**: How likely the current market is at a top (selling opportunity)

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Your First Calculation
```bash
python main.py
```

This will:
- Fetch latest Bitcoin market data
- Calculate all 21 indicators
- Generate TOP and BOTTOM scores
- Display results in your terminal
- Save results to database and files

### 3. Check System Status
```bash
python main.py --status
```

### 4. Export to Excel
```bash
python main.py --excel
```

## How It Works

### Data Sources
The system pulls data from:
- **TradingView**: Price, volume, technical indicators
- **Bitcoin Magazine Pro**: CVDD, Terminal Price, NUPL metrics
- **YCharts**: Transaction fees
- **Exchange APIs**: Funding rates

### The 21 Indicators

**BOTTOM Indicators (11)** - Detect market lows:
1. CVDD/Terminal Price Relative
2. M Timed Bottom Score
3. 2D Volume Burst
4. CM VIX Fix
5. Gaussian Channel
6. 3D MMD
7. Hash Ribbons
8. W Wavefront
9. SuperTrend
10. Pi Cycle Low
11. Puell Multiple

**TOP Indicators (10)** - Detect market highs:
1. CVDD/Terminal Price Relative
2. M Timed Top Score
3. 3D Volume
4. BBWP
5. MMD
6. Funding Rates
7. NUPL
8. WaveTrend Oscillator
9. Transaction Cost
10. Pi Cycle

### Score Interpretation

#### BOTTOM Scores
- **0.8 - 1.0**: Very Strong bottom signal (strong buy)
- **0.6 - 0.8**: Strong bottom signal (buy)
- **0.4 - 0.6**: Moderate bottom signal (consider buying)
- **0.2 - 0.4**: Weak bottom signal
- **0.0 - 0.2**: Very weak bottom signal

#### TOP Scores
- **0.8 - 1.0**: Very Strong top signal (strong sell)
- **0.6 - 0.8**: Strong top signal (sell)
- **0.4 - 0.6**: Moderate top signal (consider selling)
- **0.2 - 0.4**: Weak top signal
- **0.0 - 0.2**: Very weak top signal

## Automated Scheduling

Run calculations twice daily (8:00 and 20:00 UTC):
```bash
python scheduler/indicator_scheduler.py
```

## Output Files

The system creates:
- **SQLite Database**: `btc_indicators.db`
- **JSON Files**: Complete calculation results
- **CSV Files**: Individual indicators and summary data
- **Excel Reports**: Comprehensive analysis (with `--excel` flag)
- **Historical CSV**: Append-only files for backtesting

## Configuration

Key files in `src/config/`:
- **`weights.json`**: Adjust indicator importance
- **`bounds.json`**: Set normalization ranges
- **`data_sources.json`**: Configure data endpoints

## Common Commands

```bash
# Single calculation
python main.py

# With Excel export
python main.py --excel

# Check system status
python main.py --status

# Clean old data (30 days)
python main.py --cleanup 30

# Verbose logging
python main.py --verbose

# Start scheduler
python scheduler/indicator_scheduler.py

# Manual run via scheduler
python scheduler/indicator_scheduler.py --manual
```

## Project Structure

```
topBottom/
├── main.py                 # Main entry point
├── requirements.txt        # Dependencies
├── src/
│   ├── config/            # Configuration files
│   ├── data_adapters/     # Data source integrations
│   ├── indicators/        # Individual indicator implementations
│   │   ├── bottom/       # 11 bottom indicators
│   │   └── top/          # 10 top indicators
│   ├── composer/         # Score aggregation system
│   └── storage/          # Database and file exports
├── scheduler/            # Automated execution
├── outputs/             # Generated reports
└── tests/               # Test suite
```

## Important Notes

⚠️ **Disclaimer**: This system is for educational and research purposes only. It should not be considered financial advice. Always do your own research before making investment decisions.

⚠️ **Data Limitations**: Some adapters currently use sample data. For production use, you'll need to integrate with real APIs.

## Troubleshooting

1. **Missing Dependencies**: Run `pip install -r requirements.txt`
2. **Data Fetch Errors**: Check internet connection and data source availability
3. **Permission Issues**: Ensure write permissions for output directories
4. **Memory Issues**: The system is designed to be lightweight, but large historical datasets may require cleanup

## Next Steps

1. Run `python main.py --status` to verify installation
2. Run your first calculation with `python main.py`
3. Review the generated outputs in the `outputs/` directory
4. Customize indicator weights in `src/config/weights.json` if needed
5. Set up automated scheduling with the scheduler

## Getting Help

- Check the main `README.md` for detailed documentation
- Review log files: `btc_indicators.log` and `scheduler.log`
- Run with `--verbose` flag for detailed debugging information