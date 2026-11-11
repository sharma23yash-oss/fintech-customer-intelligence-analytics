import pandas as pd, numpy as np
from pathlib import Path
X=str(Path(__file__).resolve().parents[1]/'data'/'raw'/'Fintech_Brokerage_Customer_Analytics_Synthetic_Project.xlsx')
sh=pd.read_excel(X,sheet_name=None); u=sh['Users_10000']; m=sh['Monthly_Activity']; t=sh['Support_Tickets']
snap=pd.Timestamp('2026-10-31')
for c in ['registration_date','kyc_completion_date','bank_link_date','first_deposit_date','first_trade_date','last_active_date']: u[c]=pd.to_datetime(u[c])
u['tenure']=(snap-u.registration_date).dt.days
print('--- active_30d vs days_inactive')
print(pd.crosstab(u.active_30d,u.days_inactive_as_of_snapshot<=30))
x=u[(u.active_30d!=(u.days_inactive_as_of_snapshot<=30))]
print(x.tenure.describe().round(1).to_dict()); print('mismatch & tenure<=30:',(x.tenure<=30).sum(),' of',len(x))
print(x[['registration_date','last_active_date','days_inactive_as_of_snapshot','active_30d','churned_30d_proxy']].head(8))
print('eligible (tenure>=30):',(u.tenure>=30).sum(),' (tenure>30):',(u.tenure>30).sum())
el=u[u.tenure>=30]; print('eligible active_30d rate',el.active_30d.mean().round(4),' churn',el.churned_30d_proxy.mean().round(4),' active sum in eligible',el.active_30d.sum())
print('active_30d in NON-eligible',u[u.tenure<30].active_30d.sum(),' of',(u.tenure<30).sum())
print('--- last_active_date distribution'); print(u.last_active_date.dt.to_period('M').value_counts().sort_index().to_dict())
print('days_inactive describe',u.days_inactive_as_of_snapshot.describe().round(1).to_dict())
print('Nov-25 cohort last_active range',u[u.registration_month=='2025-11'].last_active_date.min())
print('--- censoring: events dated after snapshot by reg month')
for col,fl in [('kyc_completion_date','kyc_completed'),('bank_link_date','bank_account_linked'),('first_deposit_date','first_deposit_made'),('first_trade_date','first_trade_made')]:
    f=u[u[fl]]; print(col,'future:',(f[col]>snap).sum(),' by reg month:',f[f[col]>snap].registration_month.value_counts().sort_index().to_dict())
# time-correct (as-of snapshot) funnel
asof={k:(u[fl]&(u[col]<=snap)).sum() for k,col,fl in [('kyc','kyc_completion_date','kyc_completed'),('bank','bank_link_date','bank_account_linked'),('dep','first_deposit_date','first_deposit_made'),('trade','first_trade_date','first_trade_made')]}
print('as-of-snapshot funnel',asof,' vs flag funnel',u[['kyc_completed','bank_account_linked','first_deposit_made','first_trade_made']].sum().to_dict())
print('--- stage durations (days) median, flagged completers')
d=pd.DataFrame({'reg_kyc':(u.kyc_completion_date-u.registration_date).dt.days,'kyc_bank':(u.bank_link_date-u.kyc_completion_date).dt.days,'bank_dep':(u.first_deposit_date-u.bank_link_date).dt.days,'dep_trade':(u.first_trade_date-u.first_deposit_date).dt.days,'reg_trade':(u.first_trade_date-u.registration_date).dt.days})
print(d.describe().round(1).T)
print('--- monthly activity vs user table')
anyT=m.groupby('user_id').trade_count.sum(); u['mon_trades']=u.user_id.map(anyT)
print('users with first_trade_made=True but 0 monthly trades:',((u.first_trade_made)&(u.mon_trades==0)).sum(),' first_trade_made=False but monthly trades>0:',((~u.first_trade_made)&(u.mon_trades>0)).sum(),' users w/ any monthly trade:',(u.mon_trades>0).sum())
print('users never active in monthly:',(m.groupby('user_id').active_in_month.sum()==0).sum())
dep=m.groupby('user_id').deposit_value_inr.sum(); u['mon_dep']=u.user_id.map(dep)
print('first_deposit_made False but monthly deposits>0:',((~u.first_deposit_made)&(u.mon_dep>0)).sum(),'  True but monthly deposit==0:',((u.first_deposit_made)&(u.mon_dep==0)).sum())
la=u.set_index('user_id').last_active_date
mm=m[m.active_in_month].copy(); mm['last_m']=mm.user_id.map(la).dt.to_period('M').astype(str)
lastm=mm.groupby('user_id').activity_month.max()
u['last_active_monthly']=u.user_id.map(lastm)
print('users where last_active_date month != last active month in monthly table:',(u.last_active_date.dt.strftime('%Y-%m')!=u.last_active_monthly.fillna('none')).sum(),' monthly-never-active:',u.last_active_monthly.isna().sum())
print('active in Oct-26 monthly vs last_active_date in Oct:',m[(m.activity_month=='2026-10')&m.active_in_month].shape[0], (u.last_active_date>='2026-10-01').sum())
print('--- tickets')
t['created_date']=pd.to_datetime(t.created_date); t['age']=(snap-t.created_date).dt.days
o=t[t.status.isin(['Open','Escalated'])]; print('open/escalated tickets age (days):',o.age.describe().round(0).to_dict(),' >90d old:',(o.age>90).sum(),' >180d:',(o.age>180).sum())
print('resolution by priority'); print(t[t.status=='Resolved'].groupby('priority').agg(n=('ticket_id','size'),mean_h=('resolution_time_hours','mean'),med_h=('resolution_time_hours','median'),csat=('csat_score','mean')).round(2))
print('status by priority'); print(pd.crosstab(t.priority,t.status,normalize='index').round(3))
tu=t.merge(u[['user_id','registration_date','kyc_completed','kyc_completion_date','bank_account_linked','first_deposit_made','first_trade_made']],on='user_id')
print('KYC tickets from users who never completed KYC:',((tu.category=='KYC & verification')&~tu.kyc_completed).sum(),'of',(tu.category=='KYC & verification').sum())
print('Bank-link tickets from users not linked:',((tu.category=='Bank linking')&~tu.bank_account_linked).sum(),'of',(tu.category=='Bank linking').sum())
print('Trading tickets from users who never traded:',((tu.category=='Trading & orders')&~tu.first_trade_made).sum(),'of',(tu.category=='Trading & orders').sum())
print('Deposit tickets from users w/o deposit:',((tu.category=='Deposits & withdrawals')&~tu.first_deposit_made).sum(),'of',(tu.category=='Deposits & withdrawals').sum())
print('ticket created > 90 days after registration:',((tu.created_date-tu.registration_date).dt.days>90).sum())
print('--- outliers'); 
a=u.loc[u.first_deposit_made,'first_deposit_amount_inr']; q1,q3=a.quantile([.25,.75]); print('deposit IQR upper fence',round(q3+1.5*(q3-q1)),' n above',(a>q3+1.5*(q3-q1)).sum(),' top5',a.nlargest(5).round(0).tolist())
r=t.resolution_time_hours.dropna(); q1,q3=r.quantile([.25,.75]); print('res time fence',round(q3+1.5*(q3-q1),1),' n above',(r>q3+1.5*(q3-q1)).sum())
tv=m.trading_value_inr[m.trading_value_inr>0]; print('trading_value pctl',tv.quantile([.5,.9,.99,1]).round(0).tolist())
print('--- campaign x quality'); 
print(u.groupby('acquisition_channel').agg(n=('user_id','size'),act=('active_30d','mean'),ch30=('churned_30d_proxy','mean')).round(3))
print('--- spend per monthly? campaigns have no dates'); 
print('rows per user monthly', m.groupby('user_id').size().describe().round(1).to_dict())
