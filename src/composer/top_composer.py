import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from ..config.config_manager import ConfigManager
from ..indicators.timeframe_manager import TimeframeManager
from ..indicators.top import *

class TopComposer:
    def __init__(self, config_manager: ConfigManager, timeframe_manager: TimeframeManager):
        self.config = config_manager
        self.tf_manager = timeframe_manager
        self.logger = logging.getLogger(__name__)

        # Initialize all top indicators
        self.indicators = [
            CVDDTerminalRelativeIndicator(config_manager, timeframe_manager),
            TimedTopScoreIndicator(config_manager, timeframe_manager),
            Volume3DIndicator(config_manager, timeframe_manager),
            BBWPIndicator(config_manager, timeframe_manager),
            MMDIndicator(config_manager, timeframe_manager),
            FundingRatesIndicator(config_manager, timeframe_manager),
            NUPLIndicator(config_manager, timeframe_manager),
            WavetrendOscillatorIndicator(config_manager, timeframe_manager),
            TransactionCostIndicator(config_manager, timeframe_manager),
            PiCycleIndicator(config_manager, timeframe_manager)
        ]

    def calculate_individual_scores(self) -> Dict[str, Any]:
        """Calculate scores for all individual indicators"""
        results = {}

        for indicator in self.indicators:
            indicator_name = indicator.get_indicator_name()

            try:
                self.logger.info(f"Calculating {indicator_name}...")
                result = indicator.get_full_result()
                results[indicator_name] = result

                if result['normalized_score'] is not None:
                    self.logger.info(f"{indicator_name}: {result['normalized_score']:.4f} (weight: {result['weight']})")
                else:
                    self.logger.warning(f"{indicator_name}: Failed to calculate")

            except Exception as e:
                self.logger.error(f"Error calculating {indicator_name}: {e}")
                results[indicator_name] = {
                    'name': indicator_name,
                    'type': 'top',
                    'raw_value': None,
                    'normalized_score': None,
                    'weight': indicator.get_weight(),
                    'bounds': indicator.get_bounds(),
                    'error': str(e),
                    'timestamp': datetime.now()
                }

        return results

    def calculate_weighted_score(self, individual_scores: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate weighted composite top score"""
        valid_scores = []
        total_weight = 0
        weighted_sum = 0
        failed_indicators = []

        for indicator_name, result in individual_scores.items():
            normalized_score = result.get('normalized_score')
            weight = result.get('weight', 0)

            if normalized_score is not None:
                valid_scores.append({
                    'name': indicator_name,
                    'score': normalized_score,
                    'weight': weight,
                    'weighted_contribution': normalized_score * weight
                })
                weighted_sum += normalized_score * weight
                total_weight += weight
            else:
                failed_indicators.append(indicator_name)

        if total_weight == 0:
            self.logger.error("No valid indicators for top score calculation")
            return {
                'composite_score': None,
                'total_weight': 0,
                'valid_indicators': 0,
                'failed_indicators': failed_indicators,
                'error': 'No valid indicators'
            }

        composite_score = weighted_sum / total_weight

        # Calculate statistics
        raw_scores = [item['score'] for item in valid_scores]
        score_stats = {
            'mean': sum(raw_scores) / len(raw_scores),
            'min': min(raw_scores),
            'max': max(raw_scores),
            'std': (sum((x - sum(raw_scores) / len(raw_scores)) ** 2 for x in raw_scores) / len(raw_scores)) ** 0.5 if len(raw_scores) > 1 else 0
        }

        return {
            'composite_score': composite_score,
            'total_weight': total_weight,
            'valid_indicators': len(valid_scores),
            'failed_indicators': failed_indicators,
            'score_breakdown': valid_scores,
            'score_statistics': score_stats,
            'calculation_timestamp': datetime.now()
        }

    def generate_top_signal_interpretation(self, composite_score: float) -> Dict[str, Any]:
        """Generate human-readable interpretation of top signal"""
        if composite_score >= 0.8:
            strength = "Very Strong"
            description = "Multiple indicators suggest high probability of market top"
            color = "red"
        elif composite_score >= 0.6:
            strength = "Strong"
            description = "Several indicators suggest potential market top"
            color = "orange"
        elif composite_score >= 0.4:
            strength = "Moderate"
            description = "Mixed signals with some top indicators present"
            color = "yellow"
        elif composite_score >= 0.2:
            strength = "Weak"
            description = "Few top indicators present, market may continue rising"
            color = "yellow-green"
        else:
            strength = "Very Weak"
            description = "Top indicators not present, market likely to continue rising"
            color = "green"

        return {
            'strength': strength,
            'description': description,
            'color': color,
            'score': composite_score,
            'percentage': round(composite_score * 100, 1)
        }

    def calculate_complete_top_analysis(self) -> Dict[str, Any]:
        """Calculate complete top analysis with all components"""
        try:
            self.logger.info("Starting complete top analysis...")

            # Calculate individual indicator scores
            individual_scores = self.calculate_individual_scores()

            # Calculate weighted composite score
            composite_result = self.calculate_weighted_score(individual_scores)

            if composite_result['composite_score'] is not None:
                # Generate interpretation
                interpretation = self.generate_top_signal_interpretation(composite_result['composite_score'])

                # Combine all results
                complete_analysis = {
                    'type': 'top',
                    'composite_score': composite_result['composite_score'],
                    'interpretation': interpretation,
                    'individual_indicators': individual_scores,
                    'composition_details': composite_result,
                    'timestamp': datetime.now(),
                    'data_quality': {
                        'total_indicators': len(self.indicators),
                        'successful_calculations': composite_result['valid_indicators'],
                        'failed_calculations': len(composite_result['failed_indicators']),
                        'success_rate': composite_result['valid_indicators'] / len(self.indicators) * 100
                    }
                }

                self.logger.info(f"Top analysis complete - Score: {composite_result['composite_score']:.4f} ({interpretation['strength']})")
                return complete_analysis

            else:
                self.logger.error("Failed to calculate composite top score")
                return {
                    'type': 'top',
                    'composite_score': None,
                    'error': 'Failed to calculate composite score',
                    'individual_indicators': individual_scores,
                    'timestamp': datetime.now()
                }

        except Exception as e:
            self.logger.error(f"Error in complete top analysis: {e}")
            return {
                'type': 'top',
                'error': str(e),
                'timestamp': datetime.now()
            }