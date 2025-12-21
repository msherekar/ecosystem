"""
Temporal Pattern Analyzer for Biological Context

This module analyzes temporal patterns in user interactions
to understand workflow progression and engagement.
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any, List


class TemporalPatternAnalyzer:
    """Analyzes temporal patterns in user interactions."""
    
    def __init__(self):
        self.workflow_patterns = {
            'exploratory': {'avg_interval': 45, 'variation': 30},
            'focused': {'avg_interval': 15, 'variation': 10},
            'methodical': {'avg_interval': 60, 'variation': 20}
        }
    
    async def analyze(self, temporal_context: Dict) -> Dict[str, Any]:
        """Analyze temporal patterns for context."""
        
        current_time = datetime.now()
        session_start = temporal_context.get('session_start', current_time)
        
        # Calculate session metrics
        session_duration = (current_time - session_start).total_seconds() / 60  # in minutes
        
        # Analyze interaction patterns
        interaction_times = temporal_context.get('interaction_times', [])
        
        if len(interaction_times) > 1:
            intervals = [
                (interaction_times[i] - interaction_times[i-1]).total_seconds()
                for i in range(1, len(interaction_times))
            ]
            avg_interval = np.mean(intervals)
            interaction_pace = self._classify_interaction_pace(avg_interval)
        else:
            interaction_pace = 'unknown'
            avg_interval = 0
        
        # Detect workflow patterns
        workflow_pattern = self._detect_workflow_pattern(temporal_context)
        
        # Predict optimal intervention timing
        intervention_timing = self._predict_intervention_timing(
            session_duration, interaction_pace, workflow_pattern
        )
        
        # Assess user engagement
        engagement_level = self._assess_engagement_level(temporal_context)
        
        return {
            'session_duration': session_duration,
            'interaction_pace': interaction_pace,
            'avg_interval': avg_interval,
            'workflow_pattern': workflow_pattern,
            'optimal_intervention_timing': intervention_timing,
            'user_engagement_level': engagement_level,
            'session_stage': self._determine_session_stage(session_duration),
            'productivity_score': self._calculate_productivity_score(temporal_context)
        }
    
    def _classify_interaction_pace(self, avg_interval: float) -> str:
        """Classify user interaction pace."""
        if avg_interval < 30:
            return 'fast'
        elif avg_interval < 120:
            return 'moderate'
        else:
            return 'slow'
    
    def _detect_workflow_pattern(self, temporal_context: Dict) -> str:
        """Detect workflow pattern from temporal data."""
        interaction_times = temporal_context.get('interaction_times', [])
        query_types = temporal_context.get('query_types', [])
        
        if len(interaction_times) < 3:
            return 'unknown'
        
        # Calculate intervals
        intervals = [
            (interaction_times[i] - interaction_times[i-1]).total_seconds()
            for i in range(1, len(interaction_times))
        ]
        
        avg_interval = np.mean(intervals)
        std_interval = np.std(intervals) if len(intervals) > 1 else 0
        
        # Pattern classification
        for pattern, params in self.workflow_patterns.items():
            if (params['avg_interval'] - params['variation'] <= avg_interval <= 
                params['avg_interval'] + params['variation']):
                return pattern
        
        # Analyze query diversity for exploratory behavior
        if len(set(query_types)) / len(query_types) > 0.7:
            return 'exploratory'
        
        return 'focused'
    
    def _predict_intervention_timing(self, session_duration: float, 
                                   interaction_pace: str, workflow_pattern: str) -> Dict[str, Any]:
        """Predict optimal timing for system interventions."""
        
        base_timing = {
            'next_suggestion': 5,  # minutes
            'help_offer': 10,
            'progress_check': 15
        }
        
        # Adjust based on interaction pace
        pace_multipliers = {
            'fast': 0.5,
            'moderate': 1.0,
            'slow': 2.0
        }
        
        multiplier = pace_multipliers.get(interaction_pace, 1.0)
        
        # Adjust based on workflow pattern
        pattern_adjustments = {
            'exploratory': {'next_suggestion': 0.8, 'help_offer': 1.2},
            'focused': {'next_suggestion': 1.2, 'help_offer': 0.8},
            'methodical': {'next_suggestion': 1.0, 'help_offer': 1.0}
        }
        
        adjustments = pattern_adjustments.get(workflow_pattern, {})
        
        optimal_timing = {}
        for timing_type, base_time in base_timing.items():
            adjusted_time = base_time * multiplier
            adjusted_time *= adjustments.get(timing_type, 1.0)
            optimal_timing[timing_type] = max(adjusted_time, 1.0)  # At least 1 minute
        
        return optimal_timing
    
    def _assess_engagement_level(self, temporal_context: Dict) -> str:
        """Assess user engagement level based on temporal patterns."""
        interaction_times = temporal_context.get('interaction_times', [])
        session_start = temporal_context.get('session_start', datetime.now())
        
        if not interaction_times:
            return 'unknown'
        
        # Calculate engagement metrics
        session_duration = (datetime.now() - session_start).total_seconds() / 60
        interaction_frequency = len(interaction_times) / max(session_duration, 1)
        
        # Recent activity check
        if interaction_times:
            time_since_last = (datetime.now() - interaction_times[-1]).total_seconds() / 60
        else:
            time_since_last = session_duration
        
        # Classify engagement
        if interaction_frequency > 0.5 and time_since_last < 5:
            return 'high'
        elif interaction_frequency > 0.2 and time_since_last < 15:
            return 'medium'
        else:
            return 'low'
    
    def _determine_session_stage(self, session_duration: float) -> str:
        """Determine the current stage of the analysis session."""
        if session_duration < 5:
            return 'initial'
        elif session_duration < 20:
            return 'exploration'
        elif session_duration < 60:
            return 'analysis'
        else:
            return 'deep_work'
    
    def _calculate_productivity_score(self, temporal_context: Dict) -> float:
        """Calculate a productivity score based on temporal patterns."""
        interaction_times = temporal_context.get('interaction_times', [])
        completed_tasks = temporal_context.get('completed_tasks', 0)
        session_start = temporal_context.get('session_start', datetime.now())
        
        if not interaction_times:
            return 0.0
        
        session_duration = (datetime.now() - session_start).total_seconds() / 3600  # hours
        
        # Base productivity on tasks completed per hour
        if session_duration > 0:
            task_rate = completed_tasks / session_duration
            # Normalize to 0-1 scale (assuming 5 tasks/hour is high productivity)
            productivity_score = min(task_rate / 5.0, 1.0)
        else:
            productivity_score = 0.0
        
        return productivity_score


def main():
    """Test function for the temporal analyzer module."""
    print("Testing TemporalPatternAnalyzer...")
    
    analyzer = TemporalPatternAnalyzer()
    
    # Create mock temporal context
    now = datetime.now()
    session_start = datetime(now.year, now.month, now.day, now.hour - 1)  # 1 hour ago
    
    interaction_times = [
        session_start,
        session_start.replace(minute=session_start.minute + 5),
        session_start.replace(minute=session_start.minute + 12),
        session_start.replace(minute=session_start.minute + 25),
        session_start.replace(minute=session_start.minute + 40)
    ]
    
    temporal_context = {
        'session_start': session_start,
        'interaction_times': interaction_times,
        'query_types': ['data_upload', 'analysis', 'visualization', 'analysis', 'export'],
        'completed_tasks': 3
    }
    
    print(f"Session duration: {(now - session_start).total_seconds() / 60:.1f} minutes")
    print(f"Number of interactions: {len(interaction_times)}")
    
    # Test individual methods
    pace = analyzer._classify_interaction_pace(300)  # 5 minutes average
    print(f"Interaction pace for 5-min intervals: {pace}")
    
    pattern = analyzer._detect_workflow_pattern(temporal_context)
    print(f"Detected workflow pattern: {pattern}")
    
    engagement = analyzer._assess_engagement_level(temporal_context)
    print(f"Engagement level: {engagement}")
    
    productivity = analyzer._calculate_productivity_score(temporal_context)
    print(f"Productivity score: {productivity:.2f}")


if __name__ == "__main__":
    main() 