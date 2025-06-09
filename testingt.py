import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- Aging Factor and Trend Calculation ---
def get_aging_factor(age):
    aging_factors = {
        1: 1.0276, 2: 1.0560, 3: 1.0851, 4: 1.1151, 5: 1.1459, 6: 1.1775,
        7: 1.2100, 8: 1.2434, 9: 1.2778, 10: 1.3131, 11: 1.3493, 12: 1.3866,
        13: 1.4248, 14: 1.4642, 15: 1.5046, 16: 1.5461, 17: 1.5888, 18: 1.6327,
        19: 1.6778, 20: 1.7241, 21: 1.8025, 22: 1.8845, 23: 1.9701, 24: 2.0597,
        25: 2.1534, 26: 2.2513, 27: 2.3537, 28: 2.4607, 29: 2.5726, 30: 2.6895,
        31: 2.7707, 32: 2.8543, 33: 2.9404, 34: 3.0291, 35: 3.1205, 36: 3.2147,
        37: 3.3117, 38: 3.4116, 39: 3.5145, 40: 3.6206, 41: 3.7764, 42: 3.9388,
        43: 4.1083, 44: 4.2850, 45: 4.4694, 46: 4.6616, 47: 4.8622, 48: 5.0713,
        49: 5.2895, 50: 5.5171, 51: 5.6528, 52: 5.7918, 53: 5.9342, 54: 6.0801,
        55: 6.2296, 56: 6.3828, 57: 6.5398, 58: 6.7006, 59: 6.8654, 60: 7.0342,
        61: 7.1413, 62: 7.2499, 63: 7.3603, 64: 7.4723, 65: 7.5860, 66: 7.7127,
        67: 7.8415, 68: 7.9725, 69: 8.1057, 70: 8.2411, 71: 8.5190, 72: 8.8062,
        73: 9.1032, 74: 9.8006, 75: 10.5514, 76: 10.6875, 77: 10.8255,
        78: 10.9652, 79: 11.2544, 80: 11.5513, 81: 12.1205, 82: 12.7177,
        83: 13.3444, 84: 13.6512, 85: 13.9651, 86: 14.0337, 87: 14.1027,
        88: 14.1720
    }
    if age % 1 == 0:
        return aging_factors.get(int(age))
    elif age % 1 == 0.5:
        lower = int(age)
        upper = lower + 1
        return round((aging_factors[lower] + aging_factors[upper]) / 2, 8)
    return None

def calculate_member_risk_trend(current_age, projected_age):
    base = get_aging_factor(current_age)
    target = get_aging_factor(projected_age)
    if base is None or target is None or base == 0:
        return None
    return round(target / base, 8)

# --- Streamlit App ---
st.title("📊 Medical Claims Projection Model (with Scenario Comparison)")

st.markdown("Upload a CSV with the following columns:")
st.code("""Year, Total Claims, High-Cost, Non-Recurring, Members, Average Age, Inflation, Weight""")

uploaded_file = st.file_uploader("Upload your data file", type=["csv"])

if uploaded_file:
    df_base = pd.read_csv(uploaded_file)
    st.write("### 🔍 Raw Input Data", df_base)

    def run_projection(df, inflation_adj=0.0, age_strategy='increment_0.5'):
        df = df.copy()
        latest_age = df.iloc[-1]["Average Age"]
        projected_age = latest_age + (0.5 if age_strategy == 'increment_0.5' else 1.0 if age_strategy == 'increment_1.0' else 0)
        latest_inflation = df.iloc[-1]["Inflation"] + inflation_adj
        members = df.iloc[-1]["Members"]

        for i in df.index:
            df.at[i, "Adjusted Claims"] = df.at[i, "Total Claims"] - df.at[i, "High-Cost"] - df.at[i, "Non-Recurring"]
            trend = 1.0
            for j in range(i, len(df)):
                trend *= (1 + df.at[j, "Inflation"] + inflation_adj)
            risk_trend = calculate_member_risk_trend(df.at[i, "Average Age"], projected_age)
            df.at[i, "Medical Trend to PY"] = round(trend, 8)
            df.at[i, "Member Risk Trend to PY"] = risk_trend
            df.at[i, "Combined Trend Factor"] = round(trend * risk_trend, 8)
            df.at[i, "Projected Trended Claims"] = round(df.at[i, "Adjusted Claims"] * df.at[i, "Combined Trend Factor"], 2)
            df.at[i, "Projected PMPM"] = round(df.at[i, "Projected Trended Claims"] / (12 * df.at[i, "Members"]), 2)
            df.at[i, "Projected PMPY"] = round(df.at[i, "Projected PMPM"] * 12, 2)

        weighted_pmpm_2024 = (df["Projected PMPM"] * df["Weight"]).sum() / df["Weight"].sum()
        pmpm_2024 = weighted_pmpm_2024

        # Use pmpm_2024 as base for all future years
        results = []
        base_pmpm = pmpm_2024
        age = projected_age
        for year in [2024, 2025, 2026]:
            next_age = age + (0.5 if age_strategy == 'increment_0.5' else 1.0 if age_strategy == 'increment_1.0' else 0)
            risk_trend = calculate_member_risk_trend(age, next_age)
            inflation_factor = 1 + latest_inflation
            base_pmpm = base_pmpm * inflation_factor * risk_trend if year != 2024 else base_pmpm
            pmpy = base_pmpm * 12
            results.append({
                "Year": year,
                "Projected Age": round(next_age, 1),
                "Risk Trend": round(risk_trend, 6) if year != 2024 else None,
                "Inflation Factor": round(inflation_factor, 6) if year != 2024 else None,
                "PMPM": round(base_pmpm, 2),
                "PMPY": round(pmpy, 2)
            })
            age = next_age

        return df, pmpm_2024, pmpm_2024 * 12, pd.DataFrame(results)

    scenarios = {
        "Scenario 1 - Base Case": (0.0, 'increment_0.5'),
        "Scenario 2 - Lower Inflation, Static Age": (-0.01, 'constant'),
        "Scenario 3 - Higher Inflation, Fast Aging": (0.01, 'increment_1.0')
    }

    scenario_results = {}
    for name, (infl_adj, age_mode) in scenarios.items():
        df_out, pmpm_2024, pmpy_2024, future_proj = run_projection(df_base, infl_adj, age_mode)
        scenario_results[name] = (df_out[["Year", "Projected PMPM", "Projected PMPY"]], pmpm_2024, pmpy_2024, future_proj)

    for name, (df_summary, pmpm_2024, pmpy_2024, df_future) in scenario_results.items():
        st.write(f"### ✅ {name}:")
        st.dataframe(df_summary)
        st.write(f"📈 2024 PMPM: {round(pmpm_2024, 2)} | PMPY: {round(pmpy_2024, 2)}")
        st.dataframe(df_future)

    # Plot Comparison
    st.write("### 📊 Scenario Comparison: Projected Total Claims")
    fig, ax = plt.subplots()
    for name, (_, _, _, df_future) in scenario_results.items():
        ax.plot(df_future["Year"], df_future["PMPY"] * df_base.iloc[-1]["Members"], marker='o', label=name)
        for i, row in df_future.iterrows():
            ax.annotate(f"{int(row['Year'])}: {int(row['PMPY'] * df_base.iloc[-1]['Members']):,}",
                        (row["Year"], row["PMPY"] * df_base.iloc[-1]["Members"]),
                        textcoords="offset points", xytext=(0, 5), ha='center', fontsize=8)
    ax.set_title("Total Projected Claims Paid (PY2024–PY2026)")
    ax.set_ylabel("Claims Paid (SGD)")
    ax.set_xlabel("Policy Year")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

    # Download CSV
    csv = df_base.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Processed Data as CSV", data=csv, file_name="processed_claims.csv", mime="text/csv")
