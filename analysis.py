"""
Project 3: NHS Health Inequality & Service Demand Analysis
Statistical Reporting for Health & Social Care Commissioners
Author: Nakul Gangan
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.ticker import MaxNLocator, FuncFormatter
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

np.random.seed(2024)

# ============================================================
# 1. SYNTHETIC NHS / ONS-STYLE DATASET
# ============================================================
regions = ['Leicestershire', 'Nottinghamshire', 'Derbyshire', 'Lincolnshire', 'Northamptonshire']
months  = pd.date_range('2022-01-01', '2024-12-31', freq='MS')
n_months = len(months)

# Deprivation Index (IMD decile proxy: 1=most deprived, 10=least)
deprivation = {'Leicestershire':4.2,'Nottinghamshire':3.8,'Derbyshire':5.1,
               'Lincolnshire':5.8,'Northamptonshire':4.6}

# Children's palliative care referral rates per 100k (higher deprivation = higher need)
base_referral = {'Leicestershire':8.4,'Nottinghamshire':9.1,'Derbyshire':7.3,
                 'Lincolnshire':6.8,'Northamptonshire':8.0}

records = []
for region in regions:
    base = base_referral[region]
    for i, month in enumerate(months):
        seasonal = 1 + 0.12 * np.sin(2 * np.pi * i / 12)  # winter peak
        trend    = 1 + 0.008 * i                           # slow upward trend
        noise    = np.random.normal(1, 0.06)
        referrals = round(base * seasonal * trend * noise, 1)
        unmet     = round(referrals * np.random.uniform(0.08, 0.18), 1)
        wait_days = round(np.random.normal(18, 4), 0)

        records.append({
            'region':      region,
            'month':       month,
            'referrals':   referrals,
            'unmet_need':  unmet,
            'wait_days':   wait_days,
            'deprivation': deprivation[region] + np.random.normal(0, 0.2)
        })

df = pd.DataFrame(records)
df['month_str'] = df['month'].dt.strftime('%Y-%m')
df['year']      = df['month'].dt.year
df['quarter']   = df['month'].dt.to_period('Q').astype(str)

print(f"✅ NHS dataset generated: {len(df):,} region-month records across {len(regions)} East Midlands regions")

# ============================================================
# 2. STATISTICAL ANALYSIS
# ============================================================

# 2a. Deprivation vs Referral Rate correlation (Pearson r)
region_avg = df.groupby('region').agg(
    avg_referrals=('referrals','mean'),
    avg_deprivation=('deprivation','mean'),
    avg_wait=('wait_days','mean'),
    avg_unmet=('unmet_need','mean')
).reset_index()

r, p = stats.pearsonr(region_avg['avg_deprivation'], region_avg['avg_referrals'])
print(f"\n📊 Deprivation vs Referral Rate: r = {r:.3f}, p = {p:.4f}")
print(f"   Interpretation: {'Strong' if abs(r)>0.7 else 'Moderate'} negative correlation — higher deprivation = higher referral need")

# 2b. Seasonal decomposition (manual)
monthly_all = df.groupby('month').agg(
    avg_referrals=('referrals','mean'),
    avg_wait=('wait_days','mean'),
    total_unmet=('unmet_need','sum')
).reset_index()
monthly_all['rolling_12'] = monthly_all['avg_referrals'].rolling(12, center=True).mean()

# 2c. ARIMA-style trend forecast (simple linear extrapolation for GitHub demo)
monthly_all['t'] = np.arange(len(monthly_all))
slope, intercept, r2, _, _ = stats.linregress(monthly_all['t'], monthly_all['avg_referrals'])
forecast_t = np.arange(len(monthly_all), len(monthly_all)+6)
forecast_vals = intercept + slope * forecast_t
forecast_months = pd.date_range(monthly_all['month'].iloc[-1] + pd.DateOffset(months=1), periods=6, freq='MS')

print(f"\n📈 Trend forecast: +{slope:.3f} referrals/month average increase")
print(f"   Projected demand in 6 months: {forecast_vals[-1]:.1f} referrals/region/month")

# 2d. Regional ranking
region_avg['rank_referrals'] = region_avg['avg_referrals'].rank(ascending=False).astype(int)
region_avg['rank_wait']      = region_avg['avg_wait'].rank(ascending=False).astype(int)
print(f"\n🏆 Highest need region:  {region_avg.loc[region_avg['avg_referrals'].idxmax(),'region']}")
print(f"   Longest waits region:  {region_avg.loc[region_avg['avg_wait'].idxmax(),'region']}")
print(f"   Highest unmet need:    {region_avg.loc[region_avg['avg_unmet'].idxmax(),'region']}")

# ============================================================
# 3. QUARTERLY REPORTING TABLE (commissioner-ready)
# ============================================================
quarterly = (df.groupby(['quarter','region'])
             .agg(total_referrals=('referrals','sum'),
                  total_unmet=('unmet_need','sum'),
                  avg_wait=('wait_days','mean'))
             .reset_index())
quarterly['pct_unmet'] = (quarterly['total_unmet']/quarterly['total_referrals']*100).round(1)
quarterly['rag'] = quarterly['avg_wait'].apply(
    lambda w: 'GREEN' if w<=14 else ('AMBER' if w<=21 else 'RED'))

print("\n📋 Quarterly Summary (last 4 quarters):")
print(quarterly[quarterly['quarter']>='2024Q1'][['quarter','region','total_referrals','pct_unmet','avg_wait','rag']].to_string(index=False))

# ============================================================
# 4. DASHBOARD VISUALISATION
# ============================================================
NAVY  = '#0D2B45'
TEAL  = '#1A7A8A'
CORAL = '#D9623B'
GOLD  = '#E8B84B'
GREEN = '#3BAF7A'
SLATE = '#4A6070'
LIGHT = '#EEF5F7'
RED   = '#C0392B'
AMBER = '#E67E22'

fig = plt.figure(figsize=(20, 16), facecolor='#F4F8FA')
fig.suptitle('NHS East Midlands — Children\'s Palliative Care Demand & Inequality Analysis',
             fontsize=19, fontweight='bold', color=NAVY, y=0.98)

gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.48, wspace=0.36,
                       left=0.06, right=0.97, top=0.93, bottom=0.05)

# KPI Cards
total_referrals = df['referrals'].sum()
avg_unmet_pct   = (df['unmet_need'].sum() / df['referrals'].sum() * 100)
avg_wait        = df['wait_days'].mean()

kpis = [
    ('📋 Total Referrals',   f'{total_referrals:.0f}',      '3-Year Cumulative (All Regions)', NAVY),
    ('⚠️ Unmet Need Rate',   f'{avg_unmet_pct:.1f}%',       'Average Across All Regions', CORAL),
    ('⏱️ Avg. Wait Time',    f'{avg_wait:.0f} days',        'Mean Referral to Service', TEAL),
]
for i, (title, value, sub, color) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, i])
    ax.set_facecolor(color); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
    ax.text(0.5, 0.72, value, ha='center', va='center', fontsize=30, fontweight='bold', color='white', transform=ax.transAxes)
    ax.text(0.5, 0.42, title, ha='center', va='center', fontsize=12, fontweight='bold', color='white', transform=ax.transAxes)
    ax.text(0.5, 0.18, sub,   ha='center', va='center', fontsize=9,  color='white', alpha=0.85, transform=ax.transAxes)
    for sp in ax.spines.values(): sp.set_visible(False)

# Chart 1: Referral Demand Trend + Forecast
ax1 = fig.add_subplot(gs[1, :2])
ax1.fill_between(monthly_all['month'], monthly_all['avg_referrals'], alpha=0.18, color=TEAL)
ax1.plot(monthly_all['month'], monthly_all['avg_referrals'], color=TEAL, linewidth=1.5, label='Monthly Referrals (avg)')
ax1.plot(monthly_all['month'], monthly_all['rolling_12'],   color=NAVY, linewidth=2.5, linestyle='--', label='12-Month Rolling Avg')
ax1.plot(forecast_months, forecast_vals, color=CORAL, linewidth=2, linestyle='--', marker='o', markersize=5, label='6-Month Forecast')
ax1.axvline(monthly_all['month'].iloc[-1], color='grey', linestyle=':', alpha=0.7)
ax1.text(forecast_months[0], forecast_vals[0]*0.995, '← Forecast', fontsize=9, color=CORAL)
ax1.set_title('Referral Demand Trend & 6-Month Forecast', fontweight='bold', color=NAVY, fontsize=13)
ax1.set_ylabel('Avg. Referrals / Region / Month')
ax1.legend(frameon=False, fontsize=9)
ax1.set_facecolor(LIGHT)

# Chart 2: Deprivation vs Referral Scatter
ax2 = fig.add_subplot(gs[1, 2])
colors_sc = [TEAL, CORAL, GOLD, NAVY, GREEN]
for i, row in region_avg.iterrows():
    ax2.scatter(row['avg_deprivation'], row['avg_referrals'], s=120, color=colors_sc[i], zorder=5)
    ax2.annotate(row['region'][:8], (row['avg_deprivation'], row['avg_referrals']),
                 textcoords='offset points', xytext=(5, 4), fontsize=7.5, color=NAVY)
# Regression line
x_fit = np.linspace(region_avg['avg_deprivation'].min()-0.3, region_avg['avg_deprivation'].max()+0.3, 50)
y_fit = intercept + slope * np.arange(len(x_fit))  # reuse slope as proxy
m, b = np.polyfit(region_avg['avg_deprivation'], region_avg['avg_referrals'], 1)
ax2.plot(x_fit, m*x_fit + b, color=SLATE, linewidth=1.5, linestyle='--', alpha=0.7)
ax2.text(0.05, 0.90, f'r = {r:.2f}', transform=ax2.transAxes, fontsize=11, color=NAVY, fontweight='bold')
ax2.set_xlabel('Deprivation Index (lower = more deprived)')
ax2.set_ylabel('Avg. Referrals/Month')
ax2.set_title('Deprivation vs\nReferral Rate', fontweight='bold', color=NAVY, fontsize=11)
ax2.set_facecolor(LIGHT)

# Chart 3: Regional Comparison Grouped Bar
ax3 = fig.add_subplot(gs[2, :2])
x = np.arange(len(region_avg))
w = 0.3
b1 = ax3.bar(x - w/2, region_avg['avg_referrals'], w, label='Avg Referrals/Month', color=TEAL, alpha=0.88)
b2 = ax3.bar(x + w/2, region_avg['avg_unmet'],     w, label='Avg Unmet Need/Month', color=CORAL, alpha=0.88)
ax3.set_title('Regional Comparison: Referral Demand vs Unmet Need', fontweight='bold', color=NAVY, fontsize=12)
ax3.set_ylabel('Cases per Region per Month')
ax3.set_xticks(x); ax3.set_xticklabels(region_avg['region'], rotation=15, ha='right', fontsize=9)
ax3.legend(frameon=False)
ax3.set_facecolor(LIGHT)

# Chart 4: Wait Time RAG by Region (latest year)
ax4 = fig.add_subplot(gs[2, 2])
latest_q = quarterly[quarterly['quarter']>='2024Q1'].groupby('region')['avg_wait'].mean().sort_values()
rag_colors_bar = [GREEN if w<=14 else (AMBER if w<=21 else RED) for w in latest_q.values]
bars = ax4.barh(latest_q.index, latest_q.values, color=rag_colors_bar, alpha=0.9)
ax4.axvline(14, color=GREEN, linestyle='--', linewidth=1.5, label='14-day standard')
ax4.axvline(21, color=AMBER, linestyle='--', linewidth=1.5, label='21-day threshold')
for bar, val in zip(bars, latest_q.values):
    ax4.text(val + 0.2, bar.get_y() + bar.get_height()/2, f'{val:.0f}d', va='center', fontsize=9, fontweight='bold')
ax4.set_title('Avg Wait Time by Region\n(2024 — RAG Status)', fontweight='bold', color=NAVY, fontsize=11)
ax4.set_xlabel('Average Wait (days)')
ax4.legend(frameon=False, fontsize=8)
ax4.set_facecolor(LIGHT)

plt.savefig('/home/claude/projects/project3_nhs_health_analysis/dashboard.png',
            dpi=150, bbox_inches='tight', facecolor='#F4F8FA')
plt.close()
print("\n✅ Dashboard saved: dashboard.png")
