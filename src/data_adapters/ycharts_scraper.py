import requests
from bs4 import BeautifulSoup
import re
import time
import logging
from typing import Optional
from ..config.config_manager import ConfigManager

class YChartsScraper:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.session = requests.Session()
        self.base_config = self.config.get_data_source_config('ycharts')
        self.session.headers.update(self.base_config['headers'])
        self.logger = logging.getLogger(__name__)

    def _make_request(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        for attempt in range(retries):
            try:
                time.sleep(2)  # Rate limiting for YCharts
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == retries - 1:
                    self.logger.error(f"Failed to fetch {url} after {retries} attempts")
                    return None
                time.sleep(3 ** attempt)  # Exponential backoff
        return None

    def _extract_transaction_fee(self, soup: BeautifulSoup) -> Optional[float]:
        try:
            # YCharts specific selectors for transaction fee value
            value_selectors = [
                '.key-stat-value',
                '.indicator-value',
                '.current-value',
                '.metric-value',
                '[data-value]',
                '.yc-chart-value',
                'span[class*="value"]',
                'div[class*="value"]',
                '.stat-value'
            ]

            # Try to find the current value display
            for selector in value_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    # Look for USD values (transaction fees are typically in USD)
                    if '$' in text or 'USD' in text.upper():
                        # Extract number, handling various formats
                        numbers = re.findall(r'\$?([0-9.,]+\.?[0-9]*)', text)
                        if numbers:
                            try:
                                value = float(numbers[0].replace(',', ''))
                                if 0.01 <= value <= 1000:  # Reasonable range for BTC tx fees
                                    return value
                            except ValueError:
                                continue

            # Look for specific patterns in the page text
            text = soup.get_text()

            # Pattern 1: "Bitcoin Average Transaction Fee: $X.XX"
            fee_patterns = [
                r'Bitcoin\s+Average\s+Transaction\s+Fee[:\s]*\$?([0-9.,]+\.?[0-9]*)',
                r'Average\s+Transaction\s+Fee[:\s]*\$?([0-9.,]+\.?[0-9]*)',
                r'Transaction\s+Fee[:\s]*\$?([0-9.,]+\.?[0-9]*)',
                r'Current\s+Value[:\s]*\$?([0-9.,]+\.?[0-9]*)',
                r'\$([0-9.,]+\.?[0-9]*)\s*USD'
            ]

            for pattern in fee_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        value = float(matches[0].replace(',', ''))
                        if 0.01 <= value <= 1000:  # Sanity check
                            return value
                    except ValueError:
                        continue

            # Look for chart data in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for JSON data containing the fee value
                    if 'data' in script.string and ('fee' in script.string.lower() or 'transaction' in script.string.lower()):
                        # Extract numeric values from potential chart data
                        numbers = re.findall(r'"?(?:value|y|fee)"?\s*:\s*([0-9.]+)', script.string)
                        if numbers:
                            try:
                                value = float(numbers[-1])  # Get the latest value
                                if 0.01 <= value <= 1000:
                                    return value
                            except ValueError:
                                continue

            # Try to find table data
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if '$' in text:
                            numbers = re.findall(r'\$([0-9.,]+\.?[0-9]*)', text)
                            if numbers:
                                try:
                                    value = float(numbers[0].replace(',', ''))
                                    if 0.01 <= value <= 1000:
                                        return value
                                except ValueError:
                                    continue

        except Exception as e:
            self.logger.error(f"Error extracting transaction fee: {e}")

        return None

    def get_bitcoin_average_transaction_fee(self) -> Optional[float]:
        url = self.base_config['base_url'] + self.base_config['endpoints']['bitcoin_avg_tx_fee']
        self.logger.info(f"Fetching Bitcoin average transaction fee from: {url}")

        soup = self._make_request(url)
        if soup:
            value = self._extract_transaction_fee(soup)
            self.logger.info(f"Bitcoin average transaction fee: ${value}")
            return value
        return None

    def get_transaction_cost_normalized(self) -> Optional[float]:
        """Get transaction cost and normalize it using config bounds"""
        raw_fee = self.get_bitcoin_average_transaction_fee()
        if raw_fee is not None:
            bounds = self.config.get_indicator_bounds('top', 'transaction_cost')
            normalized = self.config.normalize_value(raw_fee, bounds)
            self.logger.info(f"Normalized transaction cost: {normalized}")
            return normalized
        return None