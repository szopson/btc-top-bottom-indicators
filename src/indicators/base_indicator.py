from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging
from ..config.config_manager import ConfigManager
from .timeframe_manager import TimeframeManager

class BaseIndicator(ABC):
    def __init__(self, config_manager: ConfigManager, timeframe_manager: TimeframeManager, indicator_type: str):
        self.config = config_manager
        self.tf_manager = timeframe_manager
        self.indicator_type = indicator_type  # 'bottom' or 'top'
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def calculate_raw_value(self) -> Optional[float]:
        """Calculate the raw indicator value"""
        pass

    @abstractmethod
    def get_indicator_name(self) -> str:
        """Get the indicator name for config lookup"""
        pass

    def get_bounds(self) -> Dict[str, float]:
        """Get normalization bounds for this indicator"""
        return self.config.get_indicator_bounds(self.indicator_type, self.get_indicator_name())

    def get_weight(self) -> float:
        """Get weight for this indicator"""
        return self.config.get_indicator_weight(self.indicator_type, self.get_indicator_name())

    def normalize_value(self, raw_value: float) -> float:
        """Normalize raw value to [0,1] range"""
        bounds = self.get_bounds()
        return self.config.normalize_value(raw_value, bounds)

    def calculate_normalized_score(self) -> Optional[float]:
        """Calculate normalized score [0,1]"""
        try:
            raw_value = self.calculate_raw_value()
            if raw_value is not None:
                normalized = self.normalize_value(raw_value)
                self.logger.info(f"{self.get_indicator_name()}: raw={raw_value:.4f}, normalized={normalized:.4f}")
                return normalized
            else:
                self.logger.warning(f"Failed to calculate raw value for {self.get_indicator_name()}")
                return None
        except Exception as e:
            self.logger.error(f"Error calculating {self.get_indicator_name()}: {e}")
            return None

    def get_full_result(self) -> Dict[str, Any]:
        """Get complete indicator result with metadata"""
        raw_value = self.calculate_raw_value()
        normalized_score = None
        if raw_value is not None:
            normalized_score = self.normalize_value(raw_value)

        return {
            'name': self.get_indicator_name(),
            'type': self.indicator_type,
            'raw_value': raw_value,
            'normalized_score': normalized_score,
            'weight': self.get_weight(),
            'bounds': self.get_bounds(),
            'timestamp': self.tf_manager.get_timeframe_data('D')['last_update'] if self.tf_manager.get_timeframe_data('D') else None
        }