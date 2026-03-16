"""Tests for the DealAnalyzer engine."""

import pytest

from app.ai.deal_analyzer import (
    CompSale,
    DealAnalyzer,
    MarketData,
    PropertyData,
)


@pytest.fixture
def analyzer():
    return DealAnalyzer()


@pytest.fixture
def sample_property():
    return PropertyData(
        address="123 Main St",
        city="Austin",
        state="TX",
        zip_code="78701",
        price=285_000,
        bedrooms=3,
        bathrooms=2.0,
        sqft=1450,
        year_built=1998,
        property_type="single_family",
        condition="fair",
        hoa_monthly=0,
        tax_annual=3420,  # 1.2% of price
        estimated_rent=2150,
    )


@pytest.fixture
def sample_market():
    return MarketData(
        city="Austin",
        state="TX",
        zip_code="78701",
        median_home_price=350_000,
        median_rent=1800,
        rent_per_sqft=1.35,
        price_per_sqft=240,
        population=1_000_000,
        population_growth_pct=2.5,
        job_growth_pct=3.0,
        unemployment_rate=3.5,
        median_income=75_000,
        crime_index=35,
        school_rating=7.5,
        price_trend_yoy_pct=4.0,
        rent_trend_yoy_pct=3.5,
    )


@pytest.fixture
def sample_comps():
    return [
        CompSale(
            address="125 Main St",
            sale_price=310_000,
            sqft=1500,
            bedrooms=3,
            bathrooms=2.0,
            year_built=2000,
            condition="good",
            distance_miles=0.2,
            days_since_sale=30,
        ),
        CompSale(
            address="200 Oak Ave",
            sale_price=295_000,
            sqft=1400,
            bedrooms=3,
            bathrooms=2.0,
            year_built=1995,
            condition="good",
            distance_miles=0.5,
            days_since_sale=60,
        ),
        CompSale(
            address="50 Elm Dr",
            sale_price=320_000,
            sqft=1600,
            bedrooms=4,
            bathrooms=2.5,
            year_built=2005,
            condition="good",
            distance_miles=1.0,
            days_since_sale=90,
        ),
    ]


class TestCapRate:
    def test_positive_cap_rate(self, analyzer, sample_property):
        cap = analyzer.calculate_cap_rate(sample_property)
        assert cap > 0
        # With $2150 rent on $285K property, cap rate should be roughly 5-9%
        assert 0.03 < cap < 0.12

    def test_zero_price_returns_zero(self, analyzer, sample_property):
        sample_property.price = 0
        assert analyzer.calculate_cap_rate(sample_property) == 0.0

    def test_higher_rent_higher_cap(self, analyzer, sample_property):
        cap_low = analyzer.calculate_cap_rate(sample_property)
        sample_property.estimated_rent = 3000
        cap_high = analyzer.calculate_cap_rate(sample_property)
        assert cap_high > cap_low


class TestCashFlow:
    def test_cash_flow_calculation(self, analyzer, sample_property):
        cf = analyzer.calculate_cash_flow(sample_property)
        # Should be a real number (could be positive or negative)
        assert isinstance(cf, float)

    def test_higher_down_payment_improves_flow(self, analyzer, sample_property):
        cf_25 = analyzer.calculate_cash_flow(sample_property, down_payment_pct=0.25)
        cf_50 = analyzer.calculate_cash_flow(sample_property, down_payment_pct=0.50)
        # More equity means less debt service, more cash flow
        assert cf_50 > cf_25

    def test_higher_rate_reduces_flow(self, analyzer, sample_property):
        cf_low = analyzer.calculate_cash_flow(sample_property, interest_rate=0.05)
        cf_high = analyzer.calculate_cash_flow(sample_property, interest_rate=0.09)
        assert cf_low > cf_high


class TestCashOnCash:
    def test_returns_ratio(self, analyzer, sample_property):
        coc = analyzer.calculate_cash_on_cash(sample_property)
        assert isinstance(coc, float)

    def test_zero_down_still_has_closing_costs(self, analyzer, sample_property):
        # 0% down still has 3% closing costs as cash invested
        coc = analyzer.calculate_cash_on_cash(sample_property, down_payment_pct=0)
        assert isinstance(coc, float)


class TestDSCR:
    def test_dscr_positive(self, analyzer, sample_property):
        dscr = analyzer.calculate_dscr(sample_property)
        assert dscr > 0

    def test_higher_rent_higher_dscr(self, analyzer, sample_property):
        dscr_low = analyzer.calculate_dscr(sample_property)
        sample_property.estimated_rent = 3500
        dscr_high = analyzer.calculate_dscr(sample_property)
        assert dscr_high > dscr_low


class TestRehabEstimate:
    def test_excellent_condition_zero(self, analyzer, sample_property):
        sample_property.condition = "excellent"
        low, high = analyzer.estimate_rehab_cost(sample_property)
        assert low == 0.0
        assert high == 0.0

    def test_poor_higher_than_fair(self, analyzer, sample_property):
        sample_property.condition = "fair"
        _, fair_high = analyzer.estimate_rehab_cost(sample_property)
        sample_property.condition = "poor"
        _, poor_high = analyzer.estimate_rehab_cost(sample_property)
        assert poor_high > fair_high

    def test_older_costs_more(self, analyzer, sample_property):
        sample_property.condition = "fair"
        sample_property.year_built = 2015
        _, new_high = analyzer.estimate_rehab_cost(sample_property)
        sample_property.year_built = 1970
        _, old_high = analyzer.estimate_rehab_cost(sample_property)
        assert old_high > new_high


class TestARV:
    def test_arv_with_comps(self, analyzer, sample_property, sample_comps):
        arv = analyzer.calculate_arv(sample_property, sample_comps)
        # ARV should be in a reasonable range around comp prices
        assert 200_000 < arv < 500_000

    def test_no_comps_returns_price(self, analyzer, sample_property):
        arv = analyzer.calculate_arv(sample_property, [])
        assert arv == sample_property.price

    def test_closer_comps_weigh_more(self, analyzer, sample_property):
        close_comp = CompSale(
            address="Next Door",
            sale_price=400_000,
            sqft=1450,
            bedrooms=3,
            bathrooms=2.0,
            year_built=1998,
            condition="good",
            distance_miles=0.1,
            days_since_sale=10,
        )
        far_comp = CompSale(
            address="Far Away",
            sale_price=200_000,
            sqft=1450,
            bedrooms=3,
            bathrooms=2.0,
            year_built=1998,
            condition="good",
            distance_miles=2.5,
            days_since_sale=300,
        )
        arv = analyzer.calculate_arv(sample_property, [close_comp, far_comp])
        # Should be closer to the close comp's price
        assert arv > 300_000


class TestBRRRR:
    def test_score_range(self, analyzer, sample_property):
        score = analyzer.calculate_brrrr_score(sample_property)
        assert 0 <= score <= 100

    def test_distressed_property_scores_higher(self, analyzer, sample_property):
        sample_property.condition = "good"
        good_score = analyzer.calculate_brrrr_score(sample_property)
        sample_property.condition = "distressed"
        dist_score = analyzer.calculate_brrrr_score(sample_property)
        # Distressed should have more equity capture potential
        assert dist_score > good_score


class TestInvestmentScore:
    def test_score_range(self, analyzer, sample_property, sample_market):
        score = analyzer.calculate_investment_score(sample_property, sample_market)
        assert 0 <= score <= 100

    def test_better_market_higher_score(self, analyzer, sample_property, sample_market):
        bad_market = MarketData(
            crime_index=80,
            school_rating=2,
            population_growth_pct=-1,
            job_growth_pct=-1,
            price_trend_yoy_pct=-5,
        )
        good_score = analyzer.calculate_investment_score(sample_property, sample_market)
        bad_score = analyzer.calculate_investment_score(sample_property, bad_market)
        assert good_score > bad_score


class TestRentEstimate:
    def test_rent_positive(self, analyzer, sample_property, sample_market):
        rent = analyzer.estimate_rent(sample_property, sample_market)
        assert rent >= 400  # minimum floor

    def test_more_beds_more_rent(self, analyzer, sample_property, sample_market):
        sample_property.bedrooms = 2
        rent_2bd = analyzer.estimate_rent(sample_property, sample_market)
        sample_property.bedrooms = 4
        rent_4bd = analyzer.estimate_rent(sample_property, sample_market)
        assert rent_4bd > rent_2bd
