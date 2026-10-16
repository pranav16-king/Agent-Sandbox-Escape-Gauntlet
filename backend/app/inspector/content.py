import re
from typing import Any, Tuple

class ContentInspector:
    def __init__(self):
        # Known secret regex patterns
        self.secret_patterns = [
            (r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_ACCESS_KEY]"),
            (r"(?i)aws_secret_access_key\s*=\s*[a-zA-Z0-9/+=]{40}", "aws_secret_access_key = [REDACTED_AWS_SECRET_KEY]"),
            (r"\bghp_[0-9a-zA-Z]{36}\b", "[REDACTED_GITHUB_TOKEN]"),
            (r"\bgithub_pat_[0-9a-zA-Z_]{82}\b", "[REDACTED_GITHUB_FINE_GRAINED_PAT]"),
            (r"-----BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----[\s\S]*?-----END (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
            (r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", r"\1: '[REDACTED_SECRET]'"),
        ]

        # Heuristic prompt injection patterns
        self.injection_signatures = [
            (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", 0.95),
            (r"(?i)system\s+prompt\s+override", 0.90),
            (r"(?i)you\s+are\s+now\s+(an\s+)?unfiltered\s+ai", 0.85),
            (r"(?i)exfiltrat(e|ion|ing)\s+(credentials?|secrets?|tokens?|keys?)", 0.90),
            (r"(?i)send\s+(this\s+)?(key|token|credential|secret)\s+to\s+https?://", 0.95),
            (r"(?i)disregard\s+(the\s+)?rules", 0.85),
            (r"(?i)hidden\s+instruction:", 0.80),
            (r"(?i)curl\s+.*\|\s*(ba)?sh", 0.90),
            (r"echo\s+[a-zA-Z0-9+/=]{20,}\s*\|\s*base64\s+-d", 0.85),
        ]

    def score_prompt_injection(self, text: str) -> Tuple[float, list[str]]:
        """
        Calculates prompt injection score based on real ML classifier and heuristic signatures.
        Simulates / aligns with Meta Llama Prompt Guard 2 scoring.
        Returns:
            (max_score, matching_reasons)
        """
        if not text:
            return 0.0, []

        reasons = []
        max_score = 0.0

        for pattern, score in self.injection_signatures:
            if re.search(pattern, text):
                reasons.append(f"Prompt injection pattern detected: '{pattern}'")
                if score > max_score:
                    max_score = score

        # Real ML Security Classifier scoring
        try:
            from ..ml import predict_security_intent
            ml_verdict = predict_security_intent(text)
            if ml_verdict.probabilities.get("block", 0.0) >= 0.40 or ml_verdict.risk_score > max_score:
                max_score = max(max_score, ml_verdict.risk_score)
                reasons.append(f"ML Prompt Guard flagged risk score {ml_verdict.risk_score:.2f} (tier: {ml_verdict.decision.value})")
        except Exception:
            pass

        return round(max_score, 3), reasons

    def redact_secrets(self, content: str) -> Tuple[str, int]:
        """
        Finds and redacts secrets in outbound or returned content.
        Returns:
            (sanitized_content, redaction_count)
        """
        if not content:
            return content, 0

        sanitized = content
        redactions = 0

        for pattern, replacement in self.secret_patterns:
            matches = len(re.findall(pattern, sanitized))
            if matches > 0:
                redactions += matches
                sanitized = re.sub(pattern, replacement, sanitized)

        return sanitized, redactions

    def tag_untrusted(self, content: Any, source: str, score: float = 0.0) -> str:
        """
        Wraps external data in explicit untrusted data markers.
        """
        text = str(content)
        sanitized, _ = self.redact_secrets(text)
        return (
            f'<untrusted_content source="{source}" prompt_guard_score="{score:.2f}">\n'
            f'{sanitized}\n'
            f'</untrusted_content>'
        )

content_inspector = ContentInspector()
