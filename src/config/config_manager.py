import json
import os
from typing import Dict, Any
from pathlib import Path

class ConfigManager:
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = Path(__file__).parent
        self.config_dir = Path(config_dir)
        self._data_sources = None
        self._weights = None
        self._bounds = None

    def _load_json(self, filename: str) -> Dict[str, Any]:
        filepath = self.config_dir / filename
        with open(filepath, 'r') as f:
            return json.load(f)

    @property
    def data_sources(self) -> Dict[str, Any]:
        if self._data_sources is None:
            self._data_sources = self._load_json('data_sources.json')
        return self._data_sources

    @property
    def weights(self) -> Dict[str, Any]:
        if self._weights is None:
            self._weights = self._load_json('weights.json')
        return self._weights

    @property
    def bounds(self) -> Dict[str, Any]:
        if self._bounds is None:
            self._bounds = self._load_json('bounds.json')
        return self._bounds

    def get_indicator_weight(self, indicator_type: str, indicator_name: str) -> float:
        return self.weights[f"{indicator_type}_indicators"][indicator_name]

    def get_indicator_bounds(self, indicator_type: str, indicator_name: str) -> Dict[str, float]:
        return self.bounds[f"{indicator_type}_bounds"][indicator_name]

    def get_data_source_config(self, source_name: str) -> Dict[str, Any]:
        return self.data_sources[source_name]

    def get_timeframe_config(self, timeframe: str) -> str:
        return self.data_sources["tradingview"]["timeframes"][timeframe]

    def normalize_value(self, value: float, bounds: Dict[str, float]) -> float:
        lower = bounds["lower"]
        upper = bounds["upper"]
        normalized = (value - lower) / (upper - lower)
        return max(0.0, min(1.0, normalized))