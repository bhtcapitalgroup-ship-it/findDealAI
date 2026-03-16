"""Unit tests for the market analysis engine (app.ai.market_analyzer)."""

import pytest

from app.ai.deal_analyzer import MarketData
from app.ai.market_analyzer import MarketAnalyzer


@pytest.fixture
def analyzer() -> MarketAnalyzer:
    return MarketAnalyzer()


@pytest.fixture
def high_growth_market() -> MarketData:
    """A booming market with strong fundamentals."""
    return MarketData(
        city="Austin",
        state="TX",
        zip_code="78701",
        median_home_price=350_000,
        median_rent=2000,
        rent_per_sqft=1.5,
        price_per_sqft=250,
        population=1_000_000,
        population_growth_pct=2.5,
        job_growth_pct=3.0,
        unemployment_rate=2.8,
        median_income=80_000,
        crime_index=25,
        school_rating=8.5,
        avg_days_on_market=15,
        inventory_months=2.5,
        price_trend_yoy_pct=6.0,
        rent_trend_yoy_pct=5.0,
        net_migration=12_000,
    )


@pytest.fixture
def declining_market() -> MarketData:
    """A struggling market with negative signals."""
    return MarketData(
        city="Declining City",
        state="OH",
        zip_code="44101",
        median_home_price=80_000,
        median_rent=700,
        rent_per_sqft=0.6,
        price_per_sqft=60,
        population=350_000,
        population_growth_pct=-0.5,
        job_growth_pct=-1.0,
        unemployment_rate=7.0,
        median_income=35_000,
        crime_index=72,
        school_rating=3.5,
        avg_days_on_market=90,
        inventory_months=8.0,
        price_trend_yoy_pct=-2.0,
        rent_trend_yoy_pct=-0.5,
        net_migration=-5_000,
    )


class TestScoreMarket:
    """Tests for MarketAnalyzer.score_market."""

    def test_score_market_high_growth(
        self, analyzer: MarketAnalyzer, high_growth_market: MarketData
    ):
        """A high-growth market should score well above 50."""
        score = analyzer.score_market(high_growth_market)
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert score >= 60  # should be clearly above average

    def test_score_market_declining(
        self, analyzer: MarketAnalyzer, declining_market: MarketData
    ):
        """A declining market should score below 50."""
        score = analyzer.score_market(declining_market)
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert score < 50

    def test_score_ordering(
        self,
        analyzer: MarketAnalyzer,
        high_growth_market: MarketData,
        declining_market: MarketData,
    ):
        """The high-growth market should outscore the declining one."""
        high_score = analyzer.score_market(high_growth_market)
        low_score = analyzer.score_market(declining_market)
        assert high_score > low_score


class TestTrendingMarkets:
    """Tests for MarketAnalyzer.identify_trending_markets."""

    def test_identify_trending_markets_sorted(
        self,
        analyzer: MarketAnalyzer,
        high_growth_market: MarketData,
        declining_market: MarketData,
    ):
        """Results should be sorted by momentum score, descending."""
        results = analyzer.identify_trending_markets(
            [declining_market, high_growth_market]
        )
        assert isinstance(results, list)
        # The high-growth market should be included; the declining one may not
        assert len(results) >= 1
        assert results[0]["city"] == "Austin"
        # Verify sorted descending by momentum_score
        for i in range(len(results) - 1):
            assert results[i]["momentum_score"] >= results[i + 1]["momentum_score"]

    def test_declining_market_excluded(
        self, analyzer: MarketAnalyzer, declining_market: MarketData
    ):
        """Markets with non-positive momentum should be excluded."""
        results = analyzer.identify_trending_markets([declining_market])
        # Declining market has negative price trend, negative pop growth,
        # and negative job growth -- momentum should be <= 0
        assert len(results) == 0


class TestMigrationScore:
    """Tests for MarketAnalyzer.calculate_migration_score."""

    def test_migration_score_positive(
        self, analyzer: MarketAnalyzer, high_growth_market: MarketData
    ):
        """Positive net migration should yield a score above 50."""
        score = analyzer.calculate_migration_score(high_growth_market)
        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert score > 50  # net_migration = +12000 is positive

    def test_migration_score_negative(
        self, analyzer: MarketAnalyzer, declining_market: MarketData
    ):
        """Negative net migration should yield a score below 50."""
        score = analyzer.calculate_migration_score(declining_market)
        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert score < 50  # net_migration = -5000

    def test_migration_score_zero_population(self, analyzer: MarketAnalyzer):
        """Zero population should return a neutral score of 50."""
        market = MarketData(population=0, net_migration=1000)
        score = analyzer.calculate_migration_score(market)
        assert score == 50.0
