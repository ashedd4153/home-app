import numpy as np
import pandas as pd
import numpy_financial as npf
from typing import Tuple, Dict, List

def compute_tax(income: float, jurisdiction: str, tax_brackets_df: pd.DataFrame) -> float:
    brackets: pd.DataFrame = tax_brackets_df[tax_brackets_df["Jurisdiction"] == jurisdiction]
    tax: float = 0
    for _, row in brackets.iterrows():
        low: float = row["Lower Bound"]
        high: float = row["Upper Bound"]
        rate: float = row["Rate"]
        if income > low:
            tax += (min(income, high) - low) * rate
            print(jurisdiction, income, high, low, rate, tax)
        else:
            break
    return tax

def compute_cash_allocation_summary(
    purchase_price: float,
    closing_costs_buy: float,
    car_budget: float,
    margin_of_safety: float,
    user_cash: float,
    fiance_cash: float,
    family_contribution: float
) -> Dict[str, float]:
    total_available_funds: float = user_cash + fiance_cash + family_contribution

    closing_cost_estimate: float = purchase_price * closing_costs_buy

    reserved_funds: float = closing_cost_estimate + car_budget + margin_of_safety
    down_payment: float = total_available_funds - reserved_funds

    cash_allocation_summary: Dict[str, float] = {
        "Total Starting Savings": total_available_funds,
        "Estimated Closing Costs": closing_cost_estimate,
        "Car Budget": car_budget,
        "Margin of Safety": margin_of_safety,
        "Reserved Funds": reserved_funds,
        "Remaining Available for Down Payment": down_payment
    }
    return cash_allocation_summary

def calculate_buy_vs_rent(
    purchase_price: float,
    mortgage_rate: float,
    loan_term: int,
    maintenance_pct: float,
    property_tax_pct: float,
    hoa_annual: float,
    home_insurance_annual: float,
    initial_rent: float,
    rent_growth: float,
    renter_insurance_annual: float,
    home_price_growth: float,
    cash_allocation_summary: Dict[str, float],
    closing_costs_buy: float,
    selling_costs: float,
    mortgage_deduction_cap: float,
    broker_fee_months: int,
    security_deposit_months: int,
    deposit_return: float,
    years: int,
    investment_return: float,
    opportunity_cost_rent: float,
    assume_tax_cuts_expire: bool,
    taxable_income: float,
    tax_brackets_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, float, float, float, Dict[str, float], float, float, float, np.ndarray, List[float], List[float], List[float], List[float], List[float], np.ndarray, np.ndarray]:

    down_payment: float = cash_allocation_summary["Remaining Available for Down Payment"]

    loan_amount: float = purchase_price - down_payment
    initial_buy_cost: float = down_payment + closing_costs_buy * purchase_price

    initial_rent_cost: float = broker_fee_months * initial_rent + security_deposit_months * initial_rent * (1 - deposit_return)

    monthly_rate: float = mortgage_rate / 12
    n_months: int = loan_term * 12
    monthly_mortgage_payment: float = npf.pmt(monthly_rate, n_months, -loan_amount)
    home_value: List[float] = [purchase_price * (1 + home_price_growth) ** i for i in range(years + 1)]
    net_sale_price: float = home_value[-1] * (1 - selling_costs)
    remaining_loan_balance: float = npf.fv(
        rate=monthly_rate,
        nper=(n_months - years * 12),
        pmt=monthly_mortgage_payment,
        pv=-loan_amount
    )
    net_proceeds: float = net_sale_price - remaining_loan_balance

    rent: List[float] = [initial_rent * (1 + rent_growth) ** i for i in range(years)]

    mortgage_payments: np.ndarray = monthly_mortgage_payment * 12 * np.ones(years)
    property_taxes: List[float] = [home_value[i] * property_tax_pct for i in range(1, years + 1)]
    maintenance_costs: List[float] = [home_value[i] * maintenance_pct for i in range(1, years + 1)]
    hoa_costs: List[float] = [hoa_annual] * years
    home_insurance: List[float] = [home_insurance_annual] * years

    interest_paid_monthly: List[float] = [npf.ipmt(monthly_rate, m, n_months, -loan_amount) for m in range(1, n_months + 1)]
    interest_paid_annual: np.ndarray = np.array(interest_paid_monthly).reshape(-1, 12).sum(axis=1)[:years]

    if assume_tax_cuts_expire:
        deductible_interest: np.ndarray = 0.5 * np.minimum(interest_paid_annual, mortgage_deduction_cap * mortgage_rate)
    else:
        deductible_interest: np.ndarray = np.zeros(years)

    federal_tax_savings: np.ndarray = np.array([
        compute_tax(taxable_income, "Federal", tax_brackets_df) -
        compute_tax(taxable_income - d, "Federal", tax_brackets_df)
        for d in deductible_interest
    ])
    nyc_tax = compute_tax(taxable_income, "NY State", tax_brackets_df) + compute_tax(taxable_income, "NYC", tax_brackets_df)
    nj_tax = compute_tax(taxable_income, "NJ", tax_brackets_df)

    state_local_tax_savings = (nyc_tax - nj_tax) * np.ones(years)

    buy_opp_cost: List[float] = [initial_buy_cost * ((1 + investment_return) ** (i+1) - (1 + investment_return) ** i) for i in range(years)]
    rent_opp_cost: List[float] = [initial_rent_cost * ((1 + investment_return) ** (i+1) - (1 + investment_return) ** i) for i in range(years)]

    rent_costs: List[float] = [r * 12 + renter_insurance_annual for r in rent]

    buy_total: float = initial_buy_cost \
                + sum(mortgage_payments) \
                + sum(property_taxes) \
                + sum(maintenance_costs) \
                + sum(hoa_costs) \
                + sum(home_insurance) \
                + sum(buy_opp_cost) \
                - sum(federal_tax_savings) \
                - sum(state_local_tax_savings) \
                - net_proceeds

    rent_total: float = initial_rent_cost \
                 + sum(rent_costs) \
                 + sum(rent_opp_cost)

    results: Dict[str, List[float]] = {
        "Initial costs": [initial_buy_cost, initial_rent_cost],
        "Recurring costs": [sum(mortgage_payments) + sum(property_taxes) + sum(maintenance_costs) + sum(hoa_costs) + sum(home_insurance) - sum(federal_tax_savings) - sum(state_local_tax_savings),
                            sum(rent_costs)],
        "Opportunity costs": [sum(buy_opp_cost), sum(rent_opp_cost)],
        "Net proceeds": [-net_proceeds, -initial_rent_cost * deposit_return],
        "Total": [buy_total, rent_total]
    }

    df: pd.DataFrame = pd.DataFrame(results, index=["Buy", "Rent"]).T

    yearly_buy_costs: List[float] = []
    yearly_rent_costs: List[float] = []

    for year in range(years):
        buy_yearly: float = (
            monthly_mortgage_payment * 12
            + property_taxes[year]
            + maintenance_costs[year]
            + hoa_costs[year]
            + home_insurance[year]
            - federal_tax_savings[year]
            - state_local_tax_savings[year]
        )
        rent_yearly: float = rent[year] * 12 + renter_insurance_annual
        yearly_buy_costs.append(buy_yearly)
        yearly_rent_costs.append(rent_yearly)

    yearly_costs_df: pd.DataFrame = pd.DataFrame({
        "Year": range(1, years + 1),
        "Buy Yearly Cost": yearly_buy_costs,
        "Rent Yearly Cost": yearly_rent_costs
    })

    # Monthly breakdown DataFrame
    n_months_total = years * 12
    months = np.arange(1, n_months_total + 1)
    monthly_mortgage_payments = np.full(n_months_total, monthly_mortgage_payment)
    monthly_insurance_payments = np.full(n_months_total, home_insurance_annual / 12)
    # Property tax: annual property taxes spread evenly across months, so recalculate for each year
    monthly_property_taxes = np.concatenate([
        np.full(12, (purchase_price * (1 + home_price_growth) ** (year+1) * property_tax_pct) / 12)
        for year in range(years)
    ])
    # Home value: purchase_price grows monthly by home_price_growth compounded monthly
    monthly_growth_rate = (1 + home_price_growth) ** (1/12) - 1
    monthly_home_values = purchase_price * (1 + monthly_growth_rate) ** np.arange(n_months_total)
    monthly_breakdown_df = pd.DataFrame({
        "Month": months,
        "Monthly Mortgage Payment": monthly_mortgage_payments,
        "Monthly Insurance Payment": monthly_insurance_payments,
        "Monthly Property Tax Payment": monthly_property_taxes,
        "Home Value": monthly_home_values
    })
    monthly_breakdown_df["Total Monthly Cost"] = (
        monthly_breakdown_df["Monthly Mortgage Payment"]
        + monthly_breakdown_df["Monthly Insurance Payment"]
        + monthly_breakdown_df["Monthly Property Tax Payment"]
    )

    # 1. First year expense analytics
    first_year_mortgage: float = monthly_mortgage_payment * 12
    first_year_property_tax: float = property_taxes[0]
    first_year_maintenance: float = maintenance_costs[0]
    first_year_hoa: float = hoa_annual
    first_year_insurance: float = home_insurance_annual
    first_year_total_recurring: float = (
        first_year_mortgage + first_year_property_tax + first_year_maintenance + first_year_hoa + first_year_insurance
    )
    first_year_expenses: Dict[str, float] = {
        "Mortgage Payments": first_year_mortgage,
        "Property Taxes": first_year_property_tax,
        "Maintenance": first_year_maintenance,
        "HOA": first_year_hoa,
        "Home Insurance": first_year_insurance,
        "Total Recurring Expenses": first_year_total_recurring
    }

    # 2. Tax savings analytics
    total_federal_savings: float = sum(federal_tax_savings)
    total_state_local_savings: float = sum(state_local_tax_savings)
    total_savings: float = total_federal_savings + total_state_local_savings

    # 2a. Estimated total taxes
    federal_tax = compute_tax(taxable_income, "Federal", tax_brackets_df)
    nj_tax = compute_tax(taxable_income, "NJ", tax_brackets_df)
    nyc_tax = compute_tax(taxable_income, "NYC", tax_brackets_df)
    total_estimated_taxes = federal_tax + nj_tax + nyc_tax

    # 4. Return all analytics
    return (
        df,
        yearly_costs_df,
        net_proceeds,
        buy_total,
        rent_total,
        first_year_expenses,
        total_federal_savings,
        total_state_local_savings,
        total_savings,
        mortgage_payments,
        property_taxes,
        maintenance_costs,
        hoa_costs,
        home_insurance,
        federal_tax_savings,
        state_local_tax_savings,
        total_estimated_taxes,
        cash_allocation_summary,
        monthly_breakdown_df,
        loan_amount
    )

def calculate_post_tax_income(taxable_income: float, tax_brackets_df: pd.DataFrame, assume_tax_cuts_expire: bool) -> float:
    federal_tax = compute_tax(taxable_income, "Federal", tax_brackets_df)
    nj_tax = compute_tax(taxable_income, "NJ", tax_brackets_df)
    return taxable_income - federal_tax - nj_tax