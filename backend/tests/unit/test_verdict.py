"""Tests for the rule-based verdict fallback."""

import pytest

from app.services.verdict import _rule_based_verdict, _parse_verdict_response


class TestRuleBasedVerdict:
    def test_good_deal(self):
        metrics = {
            "cap_rate": 8.5,
            "monthly_cash_flow": 400,
            "cash_on_cash": 12,
        }
        hood = {
            "crime_rate": 20,
            "school_rating": 8,
            "pop_growth": 2.5,
            "rent_growth": 4.5,
        }
        result = _rule_based_verdict(metrics, hood, score=75)
        assert result["verdict"] == "Good Deal"
        assert result["confidence"] == "High"
        assert len(result["risks"]) > 0
        assert len(result["opportunities"]) > 0

    def test_average_deal(self):
        metrics = {
            "cap_rate": 5.5,
            "monthly_cash_flow": 100,
            "cash_on_cash": 6,
        }
        result = _rule_based_verdict(metrics, None, score=55)
        assert result["verdict"] == "Average"

    def test_avoid_deal(self):
        metrics = {
            "cap_rate": 3,
            "monthly_cash_flow": -200,
            "cash_on_cash": 2,
        }
        hood = {
            "crime_rate": 75,
            "pop_growth": -1.5,
        }
        result = _rule_based_verdict(metrics, hood, score=25)
        assert result["verdict"] == "Avoid"
        # Should flag negative cash flow
        assert any("Negative" in r or "negative" in r.lower() for r in result["risks"])

    def test_high_crime_flagged(self):
        metrics = {"cap_rate": 7, "monthly_cash_flow": 300, "cash_on_cash": 10}
        hood = {"crime_rate": 70}
        result = _rule_based_verdict(metrics, hood, score=55)
        assert any("crime" in r.lower() for r in result["risks"])


class TestParseVerdictResponse:
    def test_valid_json(self):
        raw = '{"verdict": "Good Deal", "confidence": "High", "summary": "Great property", "risks": ["none"], "opportunities": ["growth"]}'
        result = _parse_verdict_response(raw)
        assert result["verdict"] == "Good Deal"
        assert result["confidence"] == "High"

    def test_json_with_code_fences(self):
        raw = '```json\n{"verdict": "Average", "confidence": "Medium", "summary": "OK", "risks": [], "opportunities": []}\n```'
        result = _parse_verdict_response(raw)
        assert result["verdict"] == "Average"

    def test_fallback_on_bad_json(self):
        raw = "This is a Good Deal because the cap rate is strong."
        result = _parse_verdict_response(raw)
        assert result["verdict"] == "Good Deal"
        assert result["confidence"] == "Medium"

    def test_fallback_avoid(self):
        raw = "I would avoid this property due to negative cash flow."
        result = _parse_verdict_response(raw)
        assert result["verdict"] == "Avoid"

    def test_fallback_default_average(self):
        raw = "This is a mixed bag with some ups and downs."
        result = _parse_verdict_response(raw)
        assert result["verdict"] == "Average"
