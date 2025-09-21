import requests
from bs4 import BeautifulSoup
import re
import time
import logging
from typing import Optional, Dict
from ..config.config_manager import ConfigManager

class BitcoinMagazineScraper:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.session = requests.Session()
        self.base_config = self.config.get_data_source_config('bitcoin_magazine_pro')
        self.session.headers.update(self.base_config['headers'])
        self.logger = logging.getLogger(__name__)

    def _make_request(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        for attempt in range(retries):
            try:
                time.sleep(1)  # Rate limiting
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == retries - 1:
                    self.logger.error(f"Failed to fetch {url} after {retries} attempts")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        return None

    def _extract_chart_value(self, soup: BeautifulSoup, chart_type: str) -> Optional[float]:
        try:
            # Look for common patterns in Bitcoin Magazine Pro charts
            # Pattern 1: Look for data in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for chart data patterns
                    if 'chartData' in script.string or 'data' in script.string:
                        # Extract numeric values using regex
                        numbers = re.findall(r'"?value"?\s*:\s*([0-9.-]+)', script.string)
                        if numbers:
                            return float(numbers[-1])  # Get the latest value

            # Pattern 2: Look for displayed value in specific elements
            value_selectors = [
                '.chart-value',
                '.current-value',
                '.metric-value',
                '[data-value]',
                '.value',
                'span[class*="value"]',
                'div[class*="value"]'
            ]

            for selector in value_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    # Extract number from text
                    numbers = re.findall(r'([0-9.,]+\.?[0-9]*)', text)
                    if numbers:
                        try:
                            # Remove commas and convert to float
                            value = float(numbers[0].replace(',', ''))
                            return value
                        except ValueError:
                            continue

            # Pattern 3: Look for specific Bitcoin Magazine Pro chart patterns
            if chart_type == 'cvdd':
                # CVDD specific extraction patterns
                cvdd_patterns = [
                    r'CVDD[:\s]*([0-9.,]+)',
                    r'Current[:\s]*([0-9.,]+)',
                    r'Value[:\s]*([0-9.,]+)'
                ]
                text = soup.get_text()
                for pattern in cvdd_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        try:
                            return float(matches[0].replace(',', ''))
                        except ValueError:
                            continue

            elif chart_type == 'terminal_price':
                # Terminal Price specific patterns
                terminal_patterns = [
                    r'Terminal Price[:\s]*\$?([0-9.,]+)',
                    r'Price[:\s]*\$?([0-9.,]+)',
                    r'\$([0-9.,]+)'
                ]
                text = soup.get_text()
                for pattern in terminal_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        try:
                            return float(matches[0].replace(',', ''))
                        except ValueError:
                            continue

            elif chart_type == 'nupl':
                # NUPL specific patterns (percentage)
                nupl_patterns = [
                    r'NUPL[:\s]*([0-9.-]+)%?',
                    r'Relative[:\s]+Unrealized[:\s]+Profit[:\s]*([0-9.-]+)%?',
                    r'([0-9.-]+)%'
                ]
                text = soup.get_text()
                for pattern in nupl_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        try:
                            return float(matches[0])
                        except ValueError:
                            continue

        except Exception as e:
            self.logger.error(f"Error extracting {chart_type} value: {e}")

        return None

    def get_cvdd(self) -> Optional[float]:
        url = self.base_config['base_url'] + self.base_config['endpoints']['cvdd']
        soup = self._make_request(url)
        if soup:
            value = self._extract_chart_value(soup, 'cvdd')
            self.logger.info(f"CVDD value: {value}")
            return value
        return None

    def get_terminal_price(self) -> Optional[float]:
        url = self.base_config['base_url'] + self.base_config['endpoints']['terminal_price']
        soup = self._make_request(url)
        if soup:
            value = self._extract_chart_value(soup, 'terminal_price')
            self.logger.info(f"Terminal Price value: {value}")
            return value
        return None

    def get_nupl(self) -> Optional[float]:
        url = self.base_config['base_url'] + self.base_config['endpoints']['nupl']
        soup = self._make_request(url)
        if soup:
            value = self._extract_chart_value(soup, 'nupl')
            self.logger.info(f"NUPL value: {value}")
            return value
        return None

    def get_all_metrics(self) -> Dict[str, Optional[float]]:
        return {
            'cvdd': self.get_cvdd(),
            'terminal_price': self.get_terminal_price(),
            'nupl': self.get_nupl()
        }