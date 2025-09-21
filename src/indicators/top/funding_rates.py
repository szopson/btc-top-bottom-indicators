from typing import Optional, Dict, List
import requests
import json
import time
from ..base_indicator import BaseIndicator

class FundingRatesIndicator(BaseIndicator):
    def __init__(self, config_manager, timeframe_manager):
        super().__init__(config_manager, timeframe_manager, 'top')
        self.funding_config = self.config.get_data_source_config('funding_rates')

    def get_indicator_name(self) -> str:
        return 'funding_rates'

    def get_binance_funding_rate(self) -> Optional[float]:
        """Get funding rate from Binance"""
        try:
            url = self.funding_config['binance']
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'lastFundingRate' in data:
                funding_rate = float(data['lastFundingRate']) * 100  # Convert to percentage
                return funding_rate

        except Exception as e:
            self.logger.warning(f"Failed to get Binance funding rate: {e}")

        return None

    def get_bybit_funding_rate(self) -> Optional[float]:
        """Get funding rate from Bybit"""
        try:
            url = self.funding_config['bybit']
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'result' in data and len(data['result']) > 0:
                result = data['result'][0] if isinstance(data['result'], list) else data['result']
                if 'funding_rate' in result:
                    funding_rate = float(result['funding_rate']) * 100  # Convert to percentage
                    return funding_rate

        except Exception as e:
            self.logger.warning(f"Failed to get Bybit funding rate: {e}")

        return None

    def get_okex_funding_rate(self) -> Optional[float]:
        """Get funding rate from OKEx"""
        try:
            url = self.funding_config['okex']
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'data' in data and len(data['data']) > 0:
                funding_data = data['data'][0]
                if 'fundingRate' in funding_data:
                    funding_rate = float(funding_data['fundingRate']) * 100  # Convert to percentage
                    return funding_rate

        except Exception as e:
            self.logger.warning(f"Failed to get OKEx funding rate: {e}")

        return None

    def calculate_raw_value(self) -> Optional[float]:
        """
        Calculate aggregated funding rates from major exchanges
        High positive funding rates indicate long bias and potential top risk
        """
        try:
            funding_rates = []

            # Get funding rates from multiple exchanges
            exchanges = {
                'Binance': self.get_binance_funding_rate,
                'Bybit': self.get_bybit_funding_rate,
                'OKEx': self.get_okex_funding_rate
            }

            for exchange_name, get_rate_func in exchanges.items():
                rate = get_rate_func()
                if rate is not None:
                    funding_rates.append(rate)
                    self.logger.info(f"{exchange_name} funding rate: {rate:.6f}%")
                else:
                    self.logger.warning(f"Failed to get {exchange_name} funding rate")

                time.sleep(0.5)  # Rate limiting

            if not funding_rates:
                self.logger.error("Failed to get any funding rates")
                return None

            # Calculate weighted average (equal weights for now)
            avg_funding_rate = sum(funding_rates) / len(funding_rates)

            # Convert to basis points for easier interpretation
            funding_rate_bps = avg_funding_rate * 10000  # Convert to basis points

            self.logger.info(f"Average funding rate: {avg_funding_rate:.6f}% ({funding_rate_bps:.2f} bps)")
            self.logger.info(f"Number of exchanges: {len(funding_rates)}")

            # Return as basis points (will be normalized using bounds: Lower=-50, Upper=150)
            return float(funding_rate_bps)

        except Exception as e:
            self.logger.error(f"Error calculating funding rates: {e}")
            return None