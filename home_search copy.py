#%%


import numpy as np
import pandas as pd
import numpy_financial as npf

tax_brackets_df = pd.read_csv("tax_brackets.csv")


#%% 1. Costs with Growth Rates

#    - Buying:
mortgage_rate = 0.0575
loan_term = 15
maintenance_pct = 0.01
property_tax_pct = 0.016
hoa_annual = 0
home_insurance_annual = 2900 

#    - Renting:
initial_rent = 5500
rent_growth = 0.03
renter_insurance_annual = 0

#%% 2. Assets and Appreciation

#    - Buying:
home_price_growth = 0.03

#%% 3. One-off Costs

# --- Available Funds for Down Payment ---
user_cash = 470_000
fiance_cash = 150_000
family_contribution = 100_000

total_available_funds = user_cash + fiance_cash + family_contribution
print(f"\nTotal Available Funds: ${total_available_funds:,.0f}")
#
#    - Buying:
purchase_price = 1_000_000
# down_payment = 700_000
closing_costs_buy = 0.03
selling_costs = 0.06
mortgage_deduction_cap = 750_000

# --- Reserves and Allocation Strategy ---
closing_cost_estimate = purchase_price * closing_costs_buy
car_budget = 30_000  # Example assumption
margin_of_safety = 50_000  # Emergency fund

reserved_funds = closing_cost_estimate + car_budget + margin_of_safety
down_payment = total_available_funds - reserved_funds

print(f"Estimated Closing Costs: ${closing_cost_estimate:,.0f}")
print(f"Budget for Car: ${car_budget:,.0f}")
print(f"Margin of Safety: ${margin_of_safety:,.0f}")
print(f"Remaining Available for Down Payment: ${down_payment:,.0f}")


assume_tax_cuts_expire = True
# --- Derived One-off Cost Values ---
loan_amount = purchase_price - down_payment
initial_buy_cost = down_payment + closing_costs_buy * purchase_price

#    - Renting:
broker_fee_months = 1
security_deposit_months = 1
deposit_return = 1.0
initial_rent_cost = broker_fee_months * initial_rent + security_deposit_months * initial_rent * (1 - deposit_return)

#    - Other Parameters
years = 10
investment_return = 0.045
opportunity_cost_rent = 0.01

# --- Buying Calculations ---
monthly_rate = mortgage_rate / 12
n_months = loan_term * 12
monthly_mortgage_payment = npf.pmt(monthly_rate, n_months, -loan_amount)
home_value = [purchase_price * (1 + home_price_growth) ** i for i in range(years + 1)]
net_sale_price = home_value[-1] * (1 - selling_costs)
remaining_loan_balance = npf.fv(
    rate=monthly_rate,
    nper=(n_months - years * 12),
    pmt=monthly_mortgage_payment,
    pv=-loan_amount
)
net_proceeds = net_sale_price - remaining_loan_balance

#%% 4. Logic
# --- Renting Calculations ---
rent = [initial_rent * (1 + rent_growth) ** i for i in range(years)]

# --- Recurring Costs ---
mortgage_payments = monthly_mortgage_payment * 12 * np.ones(years)
property_taxes = [home_value[i] * property_tax_pct for i in range(1, years + 1)]
maintenance_costs = [home_value[i] * maintenance_pct for i in range(1, years + 1)]
hoa_costs = [hoa_annual] * years
home_insurance = [home_insurance_annual] * years

# --- Tax Savings ---
interest_paid_monthly = [npf.ipmt(monthly_rate, m, n_months, -loan_amount) for m in range(1, n_months + 1)]
interest_paid_annual = np.array(interest_paid_monthly).reshape(-1, 12).sum(axis=1)[:years]
if assume_tax_cuts_expire:
    deductible_interest = np.minimum(interest_paid_annual, mortgage_deduction_cap * mortgage_rate)
else:
    deductible_interest = np.zeros(years)

# Define taxable income
taxable_income = 500_000

# --- Accurate State/City Tax Estimates for $500K Income ---

def compute_tax(income, jurisdiction):
    brackets = tax_brackets_df[tax_brackets_df["Jurisdiction"] == jurisdiction]
    tax = 0
    for _, row in brackets.iterrows():
        low = row["Lower Bound"]
        high = row["Upper Bound"]
        rate = row["Rate"]
        if income > low:
            tax += (min(income, high) - low) * rate
        else:
            break
    return tax

nyc_tax = compute_tax(taxable_income, "NY State") + compute_tax(taxable_income, "NYC")
nj_tax = compute_tax(taxable_income, "NJ")

nyc_effective_tax_rate = nyc_tax / taxable_income
nj_effective_tax_rate = nj_tax / taxable_income

print("\n--- Effective Tax Rates ---")
print(f"NYC Effective Tax Rate: {nyc_effective_tax_rate:.3%}")
print(f"NJ Effective Tax Rate: {nj_effective_tax_rate:.3%}")

# --- State & Local Tax Savings from NJ vs NYC ---
state_local_tax_savings = (nyc_tax - nj_tax) * np.ones(years)

federal_effective_tax_rate = 0.26  # based on expected federal rate for $500k joint income
federal_tax_savings = deductible_interest * federal_effective_tax_rate

# --- Opportunity Costs ---
buy_opp_cost = [initial_buy_cost * ((1 + investment_return) ** (i+1) - (1 + investment_return) ** i) for i in range(years)]
rent_opp_cost = [initial_rent_cost * ((1 + investment_return) ** (i+1) - (1 + investment_return) ** i) for i in range(years)]

# --- Rent Costs ---
rent_costs = [r * 12 + renter_insurance_annual for r in rent]

# --- Totals ---
buy_total = initial_buy_cost \
            + sum(mortgage_payments) \
            + sum(property_taxes) \
            + sum(maintenance_costs) \
            + sum(hoa_costs) \
            + sum(home_insurance) \
            + sum(buy_opp_cost) \
            - sum(federal_tax_savings) \
            - sum(state_local_tax_savings) \
            - net_proceeds

rent_total = initial_rent_cost \
             + sum(rent_costs) \
             + sum(rent_opp_cost)

results = {
    "Initial costs": [initial_buy_cost, initial_rent_cost],
    "Recurring costs": [sum(mortgage_payments) + sum(property_taxes) + sum(maintenance_costs) + sum(hoa_costs) + sum(home_insurance) - sum(federal_tax_savings) - sum(state_local_tax_savings),
                        sum(rent_costs)],
    "Opportunity costs": [sum(buy_opp_cost), sum(rent_opp_cost)],
    "Net proceeds": [-net_proceeds, -initial_rent_cost * deposit_return],
    "Total": [buy_total, rent_total]
}

df = pd.DataFrame(results, index=["Buy", "Rent"]).T
print(df)

print("\n--- Summary ---")
if buy_total < rent_total:
    print(f"Buying saves ${rent_total - buy_total:,.0f} over {years} years.")
else:
    print(f"Renting saves ${buy_total - rent_total:,.0f} over {years} years.")

# --- Yearly Cost Breakdown ---
yearly_buy_costs = []
yearly_rent_costs = []

for year in range(years):
    buy_yearly = (
        monthly_mortgage_payment * 12
        + property_taxes[year]
        + maintenance_costs[year]
        + hoa_costs[year]
        + home_insurance[year]
        - federal_tax_savings[year]
        - state_local_tax_savings[year]
    )
    rent_yearly = rent[year] * 12 + renter_insurance_annual
    yearly_buy_costs.append(buy_yearly)
    yearly_rent_costs.append(rent_yearly)

yearly_costs_df = pd.DataFrame({
    "Year": range(1, years + 1),
    "Buy Yearly Cost": yearly_buy_costs,
    "Rent Yearly Cost": yearly_rent_costs
})
# %%

print("\n--- Yearly Cost Breakdown ---")
print(yearly_costs_df)
# %%
print("\n--- Tax Savings Contribution Breakdown ---")
total_federal_savings = sum(federal_tax_savings)
total_state_local_savings = sum(state_local_tax_savings)
total_savings = total_federal_savings + total_state_local_savings
print(f"Total Federal Tax Savings: ${total_federal_savings:,.0f}")
print(f"Total State & Local Tax Savings: ${total_state_local_savings:,.0f}")
print(f"Combined Tax Savings: ${total_savings:,.0f}")
print(f"Total Rent Cost (including opp. cost): ${rent_total:,.0f}  <-- Total Cost of Renting")
print(f"Tax Savings as % of Rent Total: {100 * total_savings / rent_total:.1f}%")
print(f"  - Federal: {100 * total_federal_savings / rent_total:.1f}%")
print(f"  - State & Local: {100 * total_state_local_savings / rent_total:.1f}%")

print(f"\n--- Breakdown of Buying Cost Components as % of Rent Total ---")
print("Upfront Costs:")
print(f"  - Initial Buy Cost: {100 * initial_buy_cost / rent_total:.1f}%")
print("\nRecurring Costs:")
print(f"  - Mortgage Payments: {100 * sum(mortgage_payments) / rent_total:.1f}%")
print(f"  - Property Taxes: {100 * sum(property_taxes) / rent_total:.1f}%")
print(f"  - Maintenance Costs: {100 * sum(maintenance_costs) / rent_total:.1f}%")
print(f"  - HOA Fees: {100 * sum(hoa_costs) / rent_total:.1f}%")
print(f"  - Home Insurance: {100 * sum(home_insurance) / rent_total:.1f}%")
print("\nOther Costs:")
print(f"  - Opportunity Cost (Buy): {100 * sum(buy_opp_cost) / rent_total:.1f}%")
print(f"  - Net Proceeds (offset): {-100 * net_proceeds / rent_total:.1f}%")
# %%

# -- First Year Buy Case Summary ---
first_year_mortgage = monthly_mortgage_payment * 12
first_year_property_tax = property_taxes[0]
first_year_maintenance = maintenance_costs[0]
first_year_hoa = hoa_costs[0]
first_year_insurance = home_insurance[0]
first_year_total_recurring = (
    first_year_mortgage + first_year_property_tax + first_year_maintenance + first_year_hoa + first_year_insurance
)

print("\n--- First Year Buy Case Summary ---")
print(f"Mortgage Payments: ${first_year_mortgage:,.0f}")
print(f"Property Taxes: ${first_year_property_tax:,.0f}")
print(f"Maintenance: ${first_year_maintenance:,.0f}")
print(f"HOA: ${first_year_hoa:,.0f}")
print(f"Home Insurance: ${first_year_insurance:,.0f}")
print(f"Total Recurring Expenses (Year 1): ${first_year_total_recurring:,.0f}")

# Assume income variable already defined
annual_income = taxable_income
total_tax = compute_tax(annual_income, "NJ") + annual_income * federal_effective_tax_rate
net_savings = annual_income - total_tax - first_year_total_recurring

print(f"\nAnnual Income: ${annual_income:,.0f}")
print(f"Estimated Total Taxes: ${total_tax:,.0f}")
print(f"Net Savings After Recurring Expenses: ${net_savings:,.0f}")

# %%
