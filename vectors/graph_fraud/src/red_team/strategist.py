"""
Red Team Strategy Module.
Analyzes Blue Team blind spots and uses LLMs to plan the next attack.
"""

import logging
import json
import random
import os
import re
from typing import Dict, Any, List

import numpy as np

import config

logger = logging.getLogger(__name__)

class SmartEvolution:
    """
    Analyzes Blue Team's mistakes to find blind spots.
    """
    def analyze_blind_spots(self, predictions: np.ndarray, true_labels: np.ndarray, 
                            features: np.ndarray, feature_names: List[str]) -> Dict[str, Any]:
        """Characterise what the detector consistently missed this epoch."""
        is_fraud = true_labels == 1
        is_caught = (predictions == 1) & is_fraud
        is_missed = (predictions == 0) & is_fraud
        
        if is_missed.sum() == 0:
            return {}
        
        if is_caught.sum() == 0:
            return {}
        
        blind_spots = {}
        for i, fname in enumerate(feature_names):
            caught_vals = features[is_caught, i]
            missed_vals = features[is_missed, i]
            
            caught_mean = float(np.mean(caught_vals)) if len(caught_vals) > 0 else 0.0
            missed_mean = float(np.mean(missed_vals)) if len(missed_vals) > 0 else 0.0
            
            diff = abs(missed_mean - caught_mean)
            if diff > 0.01:
                blind_spots[fname] = {
                    'caught_mean': round(caught_mean, 4),
                    'missed_mean': round(missed_mean, 4),
                    'shift': round(missed_mean - caught_mean, 4),
                    'direction': 'increase' if missed_mean > caught_mean else 'decrease'
                }
        return blind_spots
    
    def generate_report(self, blind_spots: Dict[str, Any], epoch: int) -> str:
        """Human-readable summary of the blind spots found."""
        report = f"\n{'='*50}\n"
        report += f"  🔴 RED TEAM EVOLUTION REPORT — Epoch {epoch}\n"
        report += f"{'='*50}\n"
        
        if not blind_spots:
            report += "  No blind spots found — Blue Team caught everything!\n"
            report += "  Red Team will try a completely different topology next epoch.\n"
            return report
        
        report += f"  Blue Team Blind Spots Detected: {len(blind_spots)}\n\n"
        for fname, info in blind_spots.items():
            if isinstance(info, dict) and 'caught_mean' in info:
                report += f"  📌 {fname}:\n"
                report += f"     Caught fraud mean: {info['caught_mean']:.4f}\n"
                report += f"     Missed fraud mean: {info['missed_mean']:.4f}\n"
                report += f"     Shift: {info['shift']:+.4f} ({info['direction']})\n"
                report += f"     → Red Team will {info['direction']} this parameter\n\n"
        return report

class LLMRedTeamController:
    """
    GenAI-powered Red Team Strategy Advisor.
    """
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock

    def generate_strategy(self, epoch: int, blind_spots: Dict[str, Any], current_params: Dict[str, Any]) -> Dict[str, Any]:
        """Turn blind spots into concrete parameter overrides for the next epoch."""
        if not blind_spots:
            return {
                "narrative": "🤖 AI Strategist: No blind spots detected. Blue Team is highly effective. Shifting to random topology rotation.",
                "overrides": {}
            }

        if self.use_mock:
            return self._mock_llm_response(epoch, blind_spots, current_params)
        else:
            return self._real_llm_response(epoch, blind_spots, current_params)

    def _mock_llm_response(self, epoch: int, blind_spots: Dict[str, Any], current_params: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic rules-based strategy, used when no API key is set."""
        overrides = {}
        strategy_points = []

        if 'device_shared_count' in blind_spots or 'ip_shared_count' in blind_spots:
            strategy_points.append("Blue Team is clustering mules via device/IP sharing graphs.")
            overrides['device_sharing_ratio'] = random.uniform(0.05, 0.15)
            strategy_points.append(f"→ Action: Reduce device sharing to {overrides['device_sharing_ratio']:.0%} to blend with legitimate users.")

        if 'pagerank' in blind_spots:
            strategy_points.append("PageRank centrality is exposing aggregation accounts.")
            overrides['topology'] = ['star_burst', 'cross_rail']
            strategy_points.append("→ Action: Switch to Star Burst / Cross-Rail topologies to disperse funds without creating high-rank hubs.")

        if 'in_degree' in blind_spots or 'out_degree' in blind_spots:
            strategy_points.append("Node degree signatures are anomalous vs legitimate accounts.")
            overrides['noise_txn_per_mule'] = random.randint(4, 8)
            strategy_points.append(f"→ Action: Inject {overrides['noise_txn_per_mule']} noise txns per mule to normalize degree distribution.")

        if 'account_age_days' in blind_spots:
            info = blind_spots['account_age_days']
            if isinstance(info, dict) and 'direction' in info:
                if info['direction'] == 'increase':
                    overrides['mule_age_range'] = (180, 500)
                    strategy_points.append("→ Action: Use dormant/aged accounts (180-500 days) — young accounts are being flagged.")
                else:
                    overrides['mule_age_range'] = (15, 90)
                    strategy_points.append("→ Action: Use fresh accounts (15-90 days) — old accounts are being flagged.")

        if not strategy_points:
            strategy_points.append("General evasion mode: randomizing all parameters.")
            overrides['amount_mean'] = random.uniform(15000, 30000)

        narrative = f"🤖 AI STRATEGIST REPORT (Epoch {epoch}):\n  " + "\n  ".join(strategy_points)

        return {
            "narrative": narrative,
            "overrides": overrides
        }

    def _real_llm_response(self, epoch: int, blind_spots: Dict[str, Any], current_params: Dict[str, Any]) -> Dict[str, Any]:
        """Ask the LLM for a strategy and parse its response."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=config.GEMINI_API_KEY)
            model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)

            prompt = f"""You are the AI Strategist for a Red Team money laundering simulation.
Your goal is to advise the Red Team on how to evade the Blue Team's GNN fraud detector.

Current Epoch: {epoch}
Current Attack Parameters: {current_params}

The Blue Team's blind spots (features where missed fraud differs from caught fraud):
{blind_spots}

Based on these blind spots, provide:
1. A 2-3 sentence strategic narrative explaining your evasion plan.
2. Specific parameter overrides as a JSON dict. Valid keys:
   - device_sharing_ratio (float 0.05-0.5)
   - topology (list from: fan_out_fan_in, cross_rail, circular, star_burst)
   - noise_txn_per_mule (int 1-8)
   - amount_mean (float 3000-30000)
   - mule_age_range (tuple like [15, 90])
   - dwell_time_min (int 15-300)
   - dwell_time_max (int 300-3600)

Return ONLY valid JSON with keys "narrative" and "overrides"."""
            response = model.generate_content(prompt)
            text = response.text
            match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
            if match:
                text = match.group(1)
            result = json.loads(text)
            narrative = f"🤖 GEMINI STRATEGIST (Epoch {epoch}):\n  {result.get('narrative', '')}"
            return {
                "narrative": narrative,
                "overrides": result.get('overrides', {})
            }
        except Exception as e:
            logger.warning(f"⚠️ LLM API Error: {e}. Falling back to mock strategy.")
            return self._mock_llm_response(epoch, blind_spots, current_params)
