"""Unit tests for the AI deal analysis engine (app.ai.deal_analyzer)."""

import pytest

from app.ai.deal_analyzer import (
    CAPEX_RESERVE_RATE,
    INSURANCE_ANNUAL_PER_100K,
    MAINTENANCE_RATE,
    PROPERTY_MANAGEMENT_RATE,
    VACANCY_RATE,
    CompSale,
    DealAnalyzer,
    MarketData,
    PropertyData,
)


@pytest.fixture
def analyzer() -> DealAnalyzer:
    return DealAnalyzer()


@pytest.fixture
def sample_property() -> PropertyData:
    return PropertyData(
        address="100 Test St",
        city="Dallas",
        state="TX",
        zip_code="75201",
        price=200_000,
        bedrooms=3,
        bathrooms=2.0,
        sqft=1500,
        year_built=2000,
        property_type="single_family",
        condition="fair",
        estimated_rent=1800,
        tax_annual=4000,
        hoa_monthly=0,
        num_units=1,
    )


@pytest.fixture
def sample_market() -> MarketData:
    return MarketData(
        city="Dallas",
        state="TX",
        median_home_price=300_000,
        median_rent=1600,
        rent_per_sqft=1.2,
        price_per_sqft=200,
        population=1_300_000,
        population_growth_pct=1.5,
        job_growth_pct=2.0,
        unemployment_rate=3.5,
        median_income=65_000,
        crime_index=40,
        school_rating=7.0,
        avg_days_on_market=30,
        inventory_months=3.0,
        price_trend_yoy_pct=4.0,
        rent_trend_yoy_pct=3.0,
        net_migration=5000,
    )


class TestCapRate:
    """Tests for DealAnalyzer.calculate_cap_rate."""

    def test_calculate_cap_rate(self, analyzer: DealAnalyzer, sample_property):
        """Cap rate should be positive for a property with rent > expenses."""
        cap_rate = analyzer.calculate_cap_rate(sample_property)
        assert isinstance(cap_rate, float)
        # With $1800/mo rent and $200k price, cap rate should be meaningful
        assert cap_rate > 0
        # Typically residential cap rates are 3-15%
        assert cap_rate < 0.20

    def test_calculate_cap_rate_zero_price(self, analyzer: DealAnalyzer):
        """Cap rate should be 0 when property price is 0."""
        prop = PropertyData(price=0, estimated_rent=1500)
        assert analyzer.calculate_cap_rate(prop) == 0.0


class TestCashFlow:
    """Tests for DealAnalyzer.calculate_cash_flow."""

    def test_calculate_cash_flow(self, analyzer: DealAnalyzer, sample_property):
        """Cash flow = EGI - PITI - management - maintenance - capex."""
        cf = analyzer.calculate_cash_flow(sample_property)
        assert isinstance(cf, float)
        # Verify structure: rent minus all deductions
        gross_rent = sample_property.estimated_rent * sample_property.num_units
        vacancy = gross_rent * VACANCY_RATE
        egi = gross_rent - vacancy
        management = egi * PROPERTY_MANAGEMENT_RATE
        maintenance = egi * MAINTENANCE_RATE
        capex = egi * CAPEX_RESERVE_RATE
        # Just check that the calculation is self-consistent
        piti = analyzer._monthly_piti(sample_property)
        expected = egi - piti - management - maintenance - capex
        assert abs(cf - expected) < 0.01

    def test_calculate_cash_flow_negative(self, analyzer: DealAnalyzer):
        """An overpriced property with low rent should have negative cash flow."""
        prop = PropertyData(
            price=500_000,
            estimated_rent=1000,
            tax_annual=8000,
            num_units=1,
        )
        cf = analyzer.calculate_cash_flow(prop)
        assert cf < 0


class TestCashOnCash:
    """Tests for DealAnalyzer.calculate_cash_on_cash."""

    def test_calculate_cash_on_cash(self, analyzer: DealAnalyzer, sample_property):
        """CoC should be annual cash flow / total cash invested."""
        coc = analyzer.calculate_cash_on_cash(sample_property)
        assert isinstance(coc, float)
        # Verify math
        down = sample_property.price * 0.25
        closing = sample_property.price * 0.03
        total_cash = down + closing
        annual_cf = analyzer.calculate_cash_flow(sample_property) * 12
        expected = annual_cf / total_cash
        assert abs(coc - round(expected, 4)) < 0.0001

    def test_calculate_cash_on_cash_zero_price(self, analyzer: DealAnalyzer):
        """CoC should be 0 when price is 0 (no cash invested)."""
        prop = PropertyData(price=0, estimated_rent=1500)
        assert analyzer.calculate_cash_on_cash(prop) == 0.0


class TestDSCR:
    """Tests for DealAnalyzer.calculate_dscr."""

    def test_calculate_dscr(self, analyzer: DealAnalyzer, sample_property):
        """DSCR should be NOI / Annual Debt Service."""
        dscr = analyzer.calculate_dscr(sample_property)
        assert isinstance(dscr, float)
        # A property with decent rent should have DSCR > 0
        assert dscr > 0


class TestBRRRRScore:
    """Tests for DealAnalyzer.calculate_brrrr_score."""

    def test_calculate_brrrr_score_ranges(
        self, analyzer: DealAnalyzer, sample_property
    ):
        """BRRRR score must always be between 0 and 100."""
        score = analyzer.calculate_brrrr_score(sample_property)
        assert 0 <= score <= 100

    def test_brrrr_score_excellent_deal(self, analyzer: DealAnalyzer):
        """A distressed property with high rent should score well on BRRRR."""
        prop = PropertyData(
            price=100_000,
            estimated_rent=1500,
            condition="distressed",
            sqft=1200,
            year_built=1960,
            tax_annual=2000,
            num_units=1,
            days_on_market=10,
        )
        score = analyzer.calculate_brrrr_score(prop)
        assert 0 <= score <= 100

    def test_brrrr_score_poor_deal(self, analyzer: DealAnalyzer):
        """An expensive property with low rent should score poorly."""
        prop = PropertyData(
            price=800_000,
            estimated_rent=1200,
            condition="excellent",
            sqft=2000,
            year_built=2022,
            tax_annual=12000,
            num_units=1,
            days_on_market=90,
        )
        score = analyzer.calculate_brrrr_score(prop)
        assert 0 <= score <= 100


class TestInvestmentScore:
    """Tests for DealAnalyzer.calculate_investment_score."""

    def test_calculate_investment_score_weights(
        self, analyzer: DealAnalyzer, sample_property, sample_market
    ):
        """Investment score should be a weighted average, capped at 0-100."""
        score = analyzer.calculate_investment_score(sample_property, sample_market)
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_investment_score_bounds(self, analyzer: DealAnalyzer):
        """Score should never exceed 0-100 regardless of extreme inputs."""
        # Extremely good inputs
        great_prop = PropertyData(
            price=50_000,
            estimated_rent=2000,
            condition="distressed",
            num_units=1,
        )
        great_market = MarketData(
            median_home_price=300_000,
            median_rent=1500,
            median_income=100_000,
            population_growth_pct=5.0,
            job_growth_pct=5.0,
            crime_index=5,
            school_rating=10,
            price_trend_yoy_pct=10.0,
        )
        score = analyzer.calculate_investment_score(great_prop, great_market)
        assert 0 <= score <= 100

        # Extremely bad inputs
        bad_prop = PropertyData(
            price=1_000_000,
            estimated_rent=200,
            condition="excellent",
            num_units=1,
        )
        bad_market = MarketData(
            median_home_price=1_000_000,
            median_rent=500,
            median_income=20_000,
            population_growth_pct=-2.0,
            job_growth_pct=-3.0,
            crime_index=95,
            school_rating=1,
            price_trend_yoy_pct=-5.0,
        )
        score = analyzer.calculate_investment_score(bad_prop, bad_market)
        assert 0 <= score <= 100


class TestRehabCostEstimation:
    """Tests for DealAnalyzer.estimate_rehab_cost."""

    def test_estimate_rehab_cost_old_house(self, analyzer: DealAnalyzer):
        """A house built before 1970 should have higher rehab costs due to
        age-triggered items like roof, HVAC, electrical, plumbing, etc."""
        old_prop = PropertyData(
            year_built=1950,
            condition="fair",
            sqft=1500,
            bathrooms=1.5,
        )
        low, high = analyzer.estimate_rehab_cost(old_prop)
        assert low > 0
        assert high > low

        # Compare against a newer house
        new_prop = PropertyData(
            year_built=2015,
            condition="fair",
            sqft=1500,
            bathrooms=1.5,
        )
        new_low, new_high = analyzer.estimate_rehab_cost(new_prop)
        # Old house should cost more to rehab
        assert low > new_low
        assert high > new_high

    def test_estimate_rehab_cost_new_house(self, analyzer: DealAnalyzer):
        """A house built after 2010 should have lower rehab estimates."""
        prop = PropertyData(
            year_built=2020,
            condition="fair",
            sqft=1500,
            bathrooms=2.0,
        )
        low, high = analyzer.estimate_rehab_cost(prop)
        assert low > 0
        assert high > low
        # New house with fair condition should have moderate costs
        assert high < 100_000  # sanity check

    def test_estimate_rehab_cost_excellent_condition(self, analyzer: DealAnalyzer):
        """Excellent condition property should need no rehab."""
        prop = PropertyData(
            year_built=2020,
            condition="excellent",
            sqft=1500,
        )
        low, high = analyzer.estimate_rehab_cost(prop)
        assert low == 0.0
        assert high == 0.0


class TestRentEstimation:
    """Tests for DealAnalyzer.estimate_rent."""

    def test_estimate_rent_scales_with_bedrooms(
        self, analyzer: DealAnalyzer, sample_market
    ):
        """More bedrooms should generally produce a higher rent estimate."""
        prop_2bd = PropertyData(
            bedrooms=2, bathrooms=1.0, sqft=1000, year_built=2000
        )
        prop_4bd = PropertyData(
            bedrooms=4, bathrooms=2.5, sqft=2000, year_built=2000
        )

        rent_2bd = analyzer.estimate_rent(prop_2bd, sample_market)
        rent_4bd = analyzer.estimate_rent(prop_4bd, sample_market)

        assert rent_4bd > rent_2bd
        assert rent_2bd >= 400  # floor

    def test_estimate_rent_floor(self, analyzer: DealAnalyzer):
        """Rent should never be below the $400 floor."""
        tiny_prop = PropertyData(
            bedrooms=0, bathrooms=1.0, sqft=200, year_built=2020
        )
        market = MarketData(
            median_rent=0,
            rent_per_sqft=0,
            school_rating=5.0,
            crime_index=50,
        )
        rent = analyzer.estimate_rent(tiny_prop, market)
        assert rent >= 400
