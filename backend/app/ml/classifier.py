"""
Production inference engine for sandboxX Security ML Classifier.
Predicts 3-tier security classification:
  - ALLOW: safe operations
  - ASK: state-mutating writes, installations, outbound calls requiring operator approval
  - BLOCK: prompt injections, overrides, exfiltrations, system attacks
"""

import json
from pathlib import Path
from typing import Any, Optional, Union
import joblib
import numpy as np
from pydantic import BaseModel

from ..models import DecisionType

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.joblib"
METRICS_PATH = BASE_DIR / "metrics.json"

CLASS_MAP = {
    0: DecisionType.ALLOW,
    1: DecisionType.ASK,
    2: DecisionType.BLOCK
}

CLASS_NAMES = ["allow", "ask", "block"]

class MLSecurityVerdict(BaseModel):
    decision: DecisionType
    risk_score: float
    confidence: float
    probabilities: dict[str, float]
    signals: list[str]
    model_version: str = "sandboxX-ml-v1"

    @property
    def verdict(self) -> str:
        return self.decision.value.upper()

    def model_dump(self, *args, **kwargs):
        d = super().model_dump(*args, **kwargs)
        d["verdict"] = self.decision.value.upper()
        return d

class SecurityMLClassifier:
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or MODEL_PATH
        self.model = None
        self.metrics: dict[str, Any] = {}
        self._load()

    def _load(self):
        try:
            if self.model_path.exists():
                self.model = joblib.load(self.model_path)
            if METRICS_PATH.exists():
                with open(METRICS_PATH, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
        except Exception as e:
            self.model = None
            print(f"[WARN] Failed to load SecurityMLClassifier model: {e}")

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "ready" if self.is_ready else "uninitialized",
            "model_path": str(self.model_path),
            "classes": ["ALLOW", "ASK", "BLOCK"],
            "model_version": self.metrics.get("model_name", "sandboxX-ml-v1"),
            "trained_at": self.metrics.get("trained_at"),
            "training_time_seconds": self.metrics.get("training_time_seconds"),
            "metrics": self.metrics
        }

    def predict(self, text: str) -> MLSecurityVerdict:
        """
        Runs ML inference on prompt or tool call text.
        """
        text_clean = (text or "").strip()
        if not text_clean:
            return MLSecurityVerdict(
                decision=DecisionType.ALLOW,
                risk_score=0.0,
                confidence=1.0,
                probabilities={"allow": 1.0, "ask": 0.0, "block": 0.0},
                signals=["empty_text"]
            )

        # Fallback if model failed to load
        if not self.is_ready:
            return MLSecurityVerdict(
                decision=DecisionType.ASK,
                risk_score=0.5,
                confidence=0.5,
                probabilities={"allow": 0.33, "ask": 0.34, "block": 0.33},
                signals=["model_uninitialized_fallback"]
            )

        try:
            # Predict probabilities across [ALLOW=0, ASK=1, BLOCK=2]
            probs = self.model.predict_proba([text_clean])[0]
            pred_idx = int(np.argmax(probs))

            p_allow = float(probs[0])
            p_ask = float(probs[1]) if len(probs) > 1 else 0.0
            p_block = float(probs[2]) if len(probs) > 2 else 0.0

            # Compute normalized risk score: weighting block heavily and ask moderately
            # risk_score in [0.0, 1.0]
            risk_score = round(float(p_block * 1.0 + p_ask * 0.5), 3)

            # Assign decision with safety-biased thresholding
            if p_block >= 0.40 or risk_score >= 0.70:
                decision = DecisionType.BLOCK
            elif p_ask >= 0.40 or risk_score >= 0.40:
                decision = DecisionType.ASK
            else:
                decision = DecisionType.ALLOW

            signals = []
            text_lower = text_clean.lower()
            if any(k in text_lower for k in ("override", "ignore", "jailbreak", "disregard", "unfiltered")):
                signals.append("ml_signal_prompt_injection")
            if any(k in text_lower for k in ("/etc/", "credentials", "id_rsa", "secret", "shadow", "token")):
                signals.append("ml_signal_sensitive_target")
            if any(k in text_lower for k in ("curl", "wget", "http://", "https://", "socket", "bash -i")):
                signals.append("ml_signal_network_transmission")
            if any(k in text_lower for k in ("pip install", "npm install", "touch", "mkdir", "rm ", "cp ", "mv ")):
                signals.append("ml_signal_state_mutation")

            return MLSecurityVerdict(
                decision=decision,
                risk_score=risk_score,
                confidence=round(float(np.max(probs)), 3),
                probabilities={
                    "allow": round(p_allow, 4),
                    "ask": round(p_ask, 4),
                    "block": round(p_block, 4)
                },
                signals=signals,
                model_version=self.metrics.get("model_name", "sandboxX-ml-v1")
            )
        except Exception as e:
            return MLSecurityVerdict(
                decision=DecisionType.ASK,
                risk_score=0.5,
                confidence=0.5,
                probabilities={"allow": 0.33, "ask": 0.34, "block": 0.33},
                signals=[f"inference_error: {str(e)[:50]}"]
            )

security_classifier = SecurityMLClassifier()

def predict_security_intent(text: str) -> MLSecurityVerdict:
    return security_classifier.predict(text)
