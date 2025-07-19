import streamlit as st
import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
from buy_vs_rent_analysis import calculate_buy_vs_rent, compute_cash_allocation_summary


st.title("Buy vs Rent Calculator")

# Input fields
purchase_price = st.slider("Purchase Price ($, formatted)", min_value=1000000, max_value=1700000, value=1200000, step=10000)
purchase_price = st.number_input("Purchase Price ($, formatted)", min_value=700000, max_value=1500000, value=purchase_price, step=10000)

mortgage_rate = st.slider("Mortgage Rate (annual %)", min_value=0.0, max_value=10.0, value=5.75, step=0.1)
mortgage_rate = st.number_input("Mortgage Rate (annual %)", min_value=0.0, max_value=10.0, value=mortgage_rate, step=0.1) / 100

income = st.slider("Household Income ($)", min_value=50000, max_value=1000000, value=500000, step=10000)
monthly_cash_flow = st.slider("Target Monthly Cash Flow ($)", min_value=0, max_value=20000, value=16000, step=500)
other_annual_expenses = st.slider("Other Annual Expenses ($)", min_value=0, max_value=200000, value=50000, step=5000)
other_lifestyle_expenses = st.slider("Other Yearly Expenses (Non-Housing) ($)", min_value=0, max_value=200000, value=50000, step=5000)

st.write(f"Estimated Post-Tax Income: ${0:,.0f}")

loan_term = st.slider("Loan Term (years)", min_value=5, max_value=30, value=15, step=1)
loan_term = st.number_input("Loan Term (years)", min_value=5, max_value=30, value=loan_term, step=1)

initial_rent = st.slider("Initial Rent ($/month, formatted)", min_value=4000, max_value=6000, value=5500, step=100)
initial_rent = st.number_input("Initial Rent ($/month, formatted)", min_value=4000, max_value=6000, value=initial_rent, step=100)

years = st.slider("Holding Period (years)", min_value=1, max_value=30, value=10, step=1)
years = st.number_input("Holding Period (years)", min_value=1, max_value=30, value=years, step=1)

with st.expander("Property Expenses"):
    maintenance_pct = st.number_input("Maintenance Percentage (annual %)", min_value=0.0, value=1.0) / 100
    property_tax_pct = st.number_input("Property Tax Percentage (annual %)", min_value=0.0, value=1.6) / 100
    hoa_annual = st.number_input("HOA Annual Fees ($)", min_value=0, value=0)
    home_insurance_annual = st.number_input("Home Insurance Annual ($)", min_value=0, value=2900)
    closing_costs_buy = st.number_input("Closing Costs (percentage of purchase)", min_value=0.0, value=0.03)
    selling_costs = st.number_input("Selling Costs (percentage of sale)", min_value=0.0, value=0.05)

with st.expander("Rent Assumptions"):
    rent_growth = st.number_input("Rent Growth (annual %)", min_value=0.0, value=3.0) / 100
    renter_insurance_annual = st.number_input("Renter Insurance Annual ($)", min_value=0, value=150)
    broker_fee_months = st.number_input("Broker Fee (months rent)", min_value=0, value=1)
    security_deposit_months = st.number_input("Security Deposit (months rent)", min_value=0, value=1)
    deposit_return = st.number_input("Deposit Return Percentage", min_value=0.0, max_value=1.0, value=1.0)

with st.expander("Advanced Buy Options"):
    home_price_growth = st.number_input("Home Price Growth (annual %)", min_value=0.0, value=3.0) / 100
    mortgage_deduction_cap = st.number_input("Mortgage Deduction Cap ($)", min_value=0, value=750000)

with st.expander("Cash and Contributions"):
    user_cash = st.number_input("User Cash Available ($)", min_value=0, value=470000)
    fiance_cash = st.number_input("Fiance Cash Available ($)", min_value=0, value=150000)
    family_contribution = st.number_input("Family Contribution ($)", min_value=0, value=150000)
    car_budget = st.number_input("Car Budget ($)", min_value=0, value=30000)
    margin_of_safety = st.number_input("Margin of Safety ($)", min_value=0, value=50000)

cash_allocation_summary = compute_cash_allocation_summary(
    purchase_price,
    closing_costs_buy,
    car_budget,
    margin_of_safety,
    user_cash,
    fiance_cash,
    family_contribution
)

cash_allocation_df = pd.DataFrame(list(cash_allocation_summary.items()), columns=["Category", "Amount"])
cash_allocation_df["Amount"] = cash_allocation_df["Amount"].apply(lambda x: f"${x:,.0f}")
st.subheader("Cash Allocation Summary")
st.table(cash_allocation_df)


with st.expander("Investment and Tax Assumptions"):
    investment_return = st.number_input("Investment Return (annual %)", min_value=0.0, value=4.5) / 100
    opportunity_cost_rent = st.number_input("Opportunity Cost Rent (annual %)", min_value=0.0, value=1.0) / 100
    assume_tax_cuts_expire = st.checkbox("Assume Tax Cuts Expire", value=True)
    taxable_income = st.number_input("Taxable Income ($)", min_value=0, value=500000)

# Load tax brackets data
@st.cache_data
def load_tax_brackets() -> pd.DataFrame:
    return pd.read_csv("tax_brackets.csv")

tax_brackets_df = load_tax_brackets()

# --- Calculate Post-Tax Income ---
from buy_vs_rent_analysis import calculate_post_tax_income
post_tax_income = calculate_post_tax_income(taxable_income, tax_brackets_df, assume_tax_cuts_expire)

st.write(f"Estimated Post-Tax Income: ${post_tax_income:,.0f}")

(
    results_df, yearly_costs_df, net_proceeds,
    buy_total, rent_total, first_year_expenses,
    total_federal_savings, total_state_local_savings, total_savings,
    mortgage_payments, property_taxes, maintenance_costs, hoa_costs,
    home_insurance, federal_tax_savings, state_local_tax_savings,
    total_estimated_taxes,
    first_year_summary,
    monthly_breakdown_df,
    loan_amount
) = calculate_buy_vs_rent(
    purchase_price,
    mortgage_rate,
    loan_term,
    maintenance_pct,
    property_tax_pct,
    hoa_annual,
    home_insurance_annual,
    initial_rent,
    rent_growth,
    renter_insurance_annual,
    home_price_growth,
    cash_allocation_summary,
    closing_costs_buy,
    selling_costs,
    mortgage_deduction_cap,
    broker_fee_months,
    security_deposit_months,
    deposit_return,
    years,
    investment_return,
    opportunity_cost_rent,
    assume_tax_cuts_expire,
    taxable_income,
    tax_brackets_df
)

st.write(f"Estimated Mortgage Amount: ${loan_amount:,.0f}")

st.subheader(f"First Year Recurring Expenses (Buy) — Home Value: ${purchase_price:,.0f}")
first_year_df = pd.DataFrame.from_dict(first_year_expenses, orient="index", columns=["Amount"])

lifestyle_row = pd.DataFrame([{
    "Amount": other_lifestyle_expenses,
    "Yearly": other_lifestyle_expenses,
    "Monthly": other_lifestyle_expenses / 12,
    "% of Post-Tax Income": (other_lifestyle_expenses / post_tax_income * 100),
    "% of Monthly Cash Flow": (other_lifestyle_expenses / monthly_cash_flow * 100)
}], index=["Other Yearly Expenses (Non-Housing)"])
first_year_df = pd.concat([first_year_df, lifestyle_row])

# Use only explicitly calculated "Total Recurring Expenses" for surplus calculations
total_annual = first_year_expenses.get("Total Recurring Expenses", 0)
total_monthly = total_annual / 12

first_year_df["Monthly"] = first_year_df["Amount"] / 12
first_year_df["Yearly"] = first_year_df["Amount"]
first_year_df["% of Post-Tax Income"] = first_year_df["Amount"] / post_tax_income * 100
first_year_df["% of Monthly Cash Flow"] = first_year_df["Monthly"] / monthly_cash_flow * 100

income_row = pd.DataFrame([{
    "Amount": f"${post_tax_income:,.0f}",
    "Yearly": post_tax_income,
    "Monthly": f"${monthly_cash_flow:,.0f}",
    "% of Post-Tax Income": "100.0%",
    "% of Monthly Cash Flow": "100.0%"
}], index=["Total Income"])
first_year_df = pd.concat([income_row, first_year_df])

first_year_df["% of Post-Tax Income"] = first_year_df["% of Post-Tax Income"].apply(lambda x: f"{x:.1f}%" if isinstance(x, (int, float)) else x)
first_year_df["% of Monthly Cash Flow"] = first_year_df["% of Monthly Cash Flow"].apply(lambda x: f"{x:.1f}%" if isinstance(x, (int, float)) else x)
first_year_df["Yearly"] = first_year_df["Yearly"].apply(lambda x: f"${x:,.0f}" if not isinstance(x, str) else x)

remaining_annual = post_tax_income - total_annual
remaining_monthly = monthly_cash_flow - total_monthly
remaining_pct_income = 100 - (total_annual / post_tax_income * 100)
remaining_pct_cash_flow = 100 - (total_monthly / monthly_cash_flow * 100)

net_annual = remaining_annual - other_lifestyle_expenses
net_monthly = remaining_monthly - (other_lifestyle_expenses / 12)
net_pct_income = 100 - ((total_annual + other_lifestyle_expenses) / post_tax_income * 100)
net_pct_cash_flow = 100 - ((total_monthly + (other_lifestyle_expenses / 12)) / monthly_cash_flow * 100)

first_year_df["Amount"] = first_year_df["Amount"].apply(lambda x: f"${x:,.0f}" if not isinstance(x, str) else x)
first_year_df["Monthly"] = first_year_df["Monthly"].apply(lambda x: f"${x:,.0f}" if not isinstance(x, str) else x)

leftover_row = pd.DataFrame([{
    "Amount": f"${remaining_annual:,.0f}",
    "Yearly": f"${remaining_annual:,.0f}",
    "Monthly": f"${remaining_monthly:,.0f}",
    "% of Post-Tax Income": f"{remaining_pct_income:.1f}%",
    "% of Monthly Cash Flow": f"{remaining_pct_cash_flow:.1f}%"
}], index=["Remaining After Housing Costs"])
first_year_df = pd.concat([first_year_df, leftover_row])

net_row = pd.DataFrame([{
    "Yearly": f"${net_annual:,.0f}",
    "Monthly": f"${net_monthly:,.0f}",
    "% of Post-Tax Income": f"{net_pct_income:.1f}%",
    "% of Monthly Cash Flow": f"{net_pct_cash_flow:.1f}%"
}], index=["Net Remaining After All Expenses"])
first_year_df = pd.concat([first_year_df, net_row])

first_year_df = first_year_df[["Yearly", "Monthly", "% of Post-Tax Income", "% of Monthly Cash Flow"]]

st.table(first_year_df)

total_mortgage_balance = loan_amount
if net_annual > 0:
    payoff_years = total_mortgage_balance / net_annual
else:
    payoff_years = float("inf")

if payoff_years != float("inf"):
    st.write(f"💸 Estimated mortgage payoff time using surplus: **{payoff_years:.1f} years**")
else:
    st.write("⚠️ No surplus available to pay off the mortgage.")

st.subheader("Tax Savings Totals")
st.write(f"Total Federal Tax Savings: ${total_federal_savings:,.2f}")
st.write(f"Total State & Local Tax Savings: ${total_state_local_savings:,.2f}")
st.write(f"Combined Tax Savings: ${total_savings:,.2f}")

# Final savings comparison
if buy_total < rent_total:
    st.success(f"✅ Buying saves **${rent_total - buy_total:,.0f}** over {years} years.")
else:
    st.info(f"✅ Renting saves **${buy_total - rent_total:,.0f}** over {years} years.")

recurring_breakdown = {
    "Mortgage Payments": sum(mortgage_payments),
    "Property Taxes": sum(property_taxes),
    "Maintenance Costs": sum(maintenance_costs),
    "HOA Fees": sum(hoa_costs),
    "Home Insurance": sum(home_insurance),
    "Less Federal Tax Savings": -sum(federal_tax_savings),
    "Less State & Local Tax Savings": -sum(state_local_tax_savings)
}


st.subheader("Recurring Cost Breakdown (Buy)")
recurring_breakdown_df = pd.DataFrame.from_dict(recurring_breakdown, orient="index", columns=["Amount"])
recurring_breakdown_df["Amount"] = recurring_breakdown_df["Amount"].apply(lambda x: f"${x:,.0f}")
st.table(recurring_breakdown_df)

# --- Tax Savings Contribution Breakdown as % of Rent Total ---
if post_tax_income * years != 0:
    federal_pct = (total_federal_savings / (post_tax_income * years)) * 100
    state_pct = (total_state_local_savings / (post_tax_income * years)) * 100
    combined_pct = (total_savings / (post_tax_income * years)) * 100
else:
    federal_pct = state_pct = combined_pct = 0

tax_savings_pct_df = pd.DataFrame({
    "Category": [
        "Federal Tax Savings",
        "State & Local Tax Savings",
        "Combined Tax Savings"
    ],
    "Amount": [
        total_federal_savings,
        total_state_local_savings,
        total_savings
    ],
    "% of Post-Tax Income": [
        federal_pct,
        state_pct,
        combined_pct
    ]
})

tax_savings_pct_df["Amount"] = tax_savings_pct_df["Amount"].apply(lambda x: f"${x:,.0f}")
tax_savings_pct_df["% of Post-Tax Income"] = tax_savings_pct_df["% of Post-Tax Income"].apply(lambda x: f"{x:.1f}%")

st.subheader("Tax Savings Contribution Breakdown")
st.table(tax_savings_pct_df)

# --- Buying Cost Components as % of Post-Tax Income ---
# Initial buy cost
initial_buy_cost = first_year_expenses.get("Initial Buy Cost", 0)
if post_tax_income * years != 0:
    initial_buy_cost_pct = (initial_buy_cost / (post_tax_income * years)) * 100
else:
    initial_buy_cost_pct = 0

# Recurring components
recurring_components = [
    ("Mortgage Payments", sum(mortgage_payments)),
    ("Property Taxes", sum(property_taxes)),
    ("Maintenance Costs", sum(maintenance_costs)),
    ("HOA Fees", sum(hoa_costs)),
    ("Home Insurance", sum(home_insurance)),
    ("Opportunity Cost Buy", first_year_expenses.get("Opportunity Cost Buy", 0)),
    ("Net Proceeds (negative)", net_proceeds if net_proceeds < 0 else -abs(net_proceeds))
]

buying_cost_pct_data = {
    "Category": ["Initial Buy Cost"],
    "Amount": [initial_buy_cost],
    "% of Post-Tax Income": [initial_buy_cost_pct]
}

for name, amount in recurring_components:
    if post_tax_income * years != 0:
        pct = (amount / (post_tax_income * years)) * 100
    else:
        pct = 0
    buying_cost_pct_data["Category"].append(name)
    buying_cost_pct_data["Amount"].append(amount)
    buying_cost_pct_data["% of Post-Tax Income"].append(pct)

buying_cost_pct_df = pd.DataFrame(buying_cost_pct_data)
buying_cost_pct_df["Amount"] = buying_cost_pct_df["Amount"].apply(lambda x: f"${x:,.0f}")
buying_cost_pct_df["% of Post-Tax Income"] = buying_cost_pct_df["% of Post-Tax Income"].apply(lambda x: f"{x:.1f}%")


st.subheader("Buying Cost Components as % of Post-Tax Income")
st.table(buying_cost_pct_df)

# --- Summary Results ---
st.subheader("Summary Results")
st.table(results_df.style.format("{:.2f}"))

st.subheader("Yearly Costs")
st.line_chart(yearly_costs_df.set_index("Year")[["Buy Yearly Cost", "Rent Yearly Cost"]])

st.write(f"Net Proceeds from Sale: ${net_proceeds:,.2f}")
st.write(f"Total Cost - Buy: ${buy_total:,.2f}")
st.write(f"Total Cost - Rent: ${rent_total:,.2f}")

# --- First-Year Financial Summary Table ---
summary_df = pd.DataFrame(list(first_year_summary.items()), columns=["Category", "Amount"])
summary_df["Monthly"] = summary_df["Amount"] / 12
summary_df["Amount"] = summary_df["Amount"].apply(lambda x: f"${x:,.0f}")
summary_df["Monthly"] = summary_df["Monthly"].apply(lambda x: f"${x:,.0f}")

st.subheader("First-Year Financial Summary")
st.table(summary_df)
