"""Phase 1 - read-only audit of the synthetic brokerage dataset. Does NOT modify raw files."""
import pandas as pd, numpy as np, sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=str(ROOT/'data'/'raw')+'/'
X=RAW+'Fintech_Brokerage_Customer_Analytics_Synthetic_Project.xlsx'
sh=pd.read_excel(X,sheet_name=None)
csv=pd.read_csv(RAW+'Fintech_Users_10000_Synthetic.csv')
u=sh['Users_10000']; m=sh['Monthly_Activity']; t=sh['Support_Tickets']; c=sh['Campaigns']; co=sh['Cohort_Retention']
out=[]
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.append(s)
P('== SHAPES'); [P(k,v.shape) for k,v in sh.items()]; P('csv',csv.shape)
P('\n== CSV vs Excel Users sheet identical?')
a=csv.copy(); b=u.copy()
for col in a.columns:
    if 'date' in col or col=='registration_month':
        a[col]=a[col].astype(str); b[col]=b[col].astype(str).str.slice(0,10 if 'date' in col else 7)
same=(a.fillna('NA').astype(str).values==b[a.columns].fillna('NA').astype(str).values)
P('cells differing:',(~same).sum())
P('\n== DTYPES users'); P(u.dtypes.to_string())
P('\n== NULLS'); 
for n,d in [('users',u),('monthly',m),('tickets',t),('campaigns',c),('cohort',co)]:
    nn=d.isna().sum(); P(n, nn[nn>0].to_dict())
P('\n== PK / dupes')
P('users dup user_id',u.user_id.duplicated().sum(),' full-row dup',u.duplicated().sum())
P('monthly dup (user,month)',m.duplicated(['user_id','activity_month']).sum())
P('tickets dup ticket_id',t.ticket_id.duplicated().sum())
P('campaign dup',c.campaign_id.duplicated().sum())
P('\n== FK')
P('monthly users not in users',(~m.user_id.isin(u.user_id)).sum(),' tickets users not in users',(~t.user_id.isin(u.user_id)).sum())
P('users campaign not in campaigns',(~u.acquisition_campaign_id.isin(c.campaign_id)).sum())
P('users with no monthly rows',(~u.user_id.isin(m.user_id)).sum())
P('\n== Categorical values')
for col in ['acquisition_channel','source_platform','city','age_group','device_type','risk_profile','first_trade_segment']:
    P(col,u[col].value_counts(dropna=False).to_dict())
for col in ['category','priority','status']: P(col,t[col].value_counts(dropna=False).to_dict())
P('\n== Channel<->campaign mapping consistency')
mp=u.groupby('acquisition_campaign_id')[['acquisition_channel','source_platform']].nunique(); P(mp.max().to_dict())
cc=u.merge(c[['campaign_id','channel','source_platform']],left_on='acquisition_campaign_id',right_on='campaign_id',suffixes=('','_c'))
P('channel mismatch users vs campaigns',(cc.acquisition_channel!=cc.channel).sum(),' platform mismatch',(cc.source_platform!=cc.source_platform_c).sum())
P('\n== Date ranges')
for col in ['registration_date','kyc_completion_date','bank_link_date','first_deposit_date','first_trade_date','last_active_date']:
    d=pd.to_datetime(u[col]); P(col,d.min(),d.max(),'nulls',d.isna().sum())
P('monthly range',m.activity_month.min(),m.activity_month.max(),' ticket range',t.created_date.min(),t.created_date.max())
P('registration_month matches date', (pd.to_datetime(u.registration_date).dt.strftime('%Y-%m')!=u.registration_month).sum(),'mismatches')
snap=pd.Timestamp('2026-10-31')
for col in ['registration_date','kyc_completion_date','bank_link_date','first_deposit_date','first_trade_date','last_active_date']:
    P('future dates >snapshot',col,(pd.to_datetime(u[col])>snap).sum())
P('\n== FLAG vs DATE consistency')
for f,d in [('kyc_completed','kyc_completion_date'),('bank_account_linked','bank_link_date'),('first_deposit_made','first_deposit_date'),('first_trade_made','first_trade_date')]:
    P(f,'True but date null',((u[f])&u[d].isna()).sum(),' False but date present',((~u[f])&u[d].notna()).sum())
P('\n== FUNNEL LOGIC (stage order & skipping)')
R,K,B,D,T=[pd.to_datetime(u[x]) for x in ['registration_date','kyc_completion_date','bank_link_date','first_deposit_date','first_trade_date']]
P('bank linked without KYC',(u.bank_account_linked&~u.kyc_completed).sum())
P('deposit without bank link',(u.first_deposit_made&~u.bank_account_linked).sum(),' deposit without KYC',(u.first_deposit_made&~u.kyc_completed).sum())
P('trade without deposit',(u.first_trade_made&~u.first_deposit_made).sum(),' trade without bank',(u.first_trade_made&~u.bank_account_linked).sum())
P('KYC<reg',(K<R).sum(),' bank<KYC',(B<K).sum(),' deposit<bank',(D<B).sum(),' trade<deposit',(T<D).sum(),' trade<reg',(T<R).sum())
P('deposit amt>0 w/o deposit',((u.first_deposit_amount_inr>0)&~u.first_deposit_made).sum(),' deposit w/ amt<=0',((u.first_deposit_amount_inr<=0)&u.first_deposit_made).sum())
P('deposit amt describe',u.loc[u.first_deposit_made,'first_deposit_amount_inr'].describe().round(1).to_dict())
P('trade segment null while trade made',(u.first_trade_made&u.first_trade_segment.isna()).sum(),' segment present w/o trade',(~u.first_trade_made&u.first_trade_segment.notna()).sum())
P('\n== ACTIVITY / CHURN LOGIC')
L=pd.to_datetime(u.last_active_date)
P('last_active < registration',(L<R).sum(),' last_active < first_trade_date',(L<T).sum(),' last_active<first_deposit',(L<D).sum(),' last_active < kyc',(L<K).sum())
calc=(snap-L).dt.days
P('days_inactive recompute mismatch',(calc!=u.days_inactive_as_of_snapshot).sum())
P('churn30 vs days>30 mismatch',((u.days_inactive_as_of_snapshot>30)!=u.churned_30d_proxy).sum(),' churn90 vs days>90 mismatch',((u.days_inactive_as_of_snapshot>90)!=u.churned_90d_proxy).sum())
P('churn90 True but churn30 False',(u.churned_90d_proxy&~u.churned_30d_proxy).sum())
P('active_30d + churned_30d both True',(u.active_30d&u.churned_30d_proxy).sum(),' both False',(~u.active_30d&~u.churned_30d_proxy).sum())
P('active_30d vs days<=30 mismatch',(u.active_30d!=(u.days_inactive_as_of_snapshot<=30)).sum())
P('churn30 rate over ALL users',u.churned_30d_proxy.mean().round(4),' churn90 rate',u.churned_90d_proxy.mean().round(4))
P('churn rate among users reg<30d before snapshot', u[R>snap-pd.Timedelta(days=30)].churned_30d_proxy.mean())
P('n users registered in last 30d',(R>snap-pd.Timedelta(days=30)).sum(),' last 90d',(R>snap-pd.Timedelta(days=90)).sum())
P('days_inactive vs days since registration: users with inactivity > tenure',((u.days_inactive_as_of_snapshot>(snap-R).dt.days)).sum())
P('\n== SUMMARY SHEET RECONCILIATION')
P('KYC',u.kyc_completed.sum(),'bank',u.bank_account_linked.sum(),'dep',u.first_deposit_made.sum(),'trade',u.first_trade_made.sum())
P('active_30d sum',u.active_30d.sum(),' churned_30d sum',u.churned_30d_proxy.sum(),' churned_90 sum',u.churned_90d_proxy.sum())
P('Funnel_Summary says active 4820 and churn 6758 (eligible) -> active+churn',4820+6758,'(must equal eligible N)')
P('Analysis_Summary active rate .5275 vs actual active_30d mean',u.active_30d.mean().round(4))
P('\n== CAMPAIGN SHEET RECONCILIATION')
g=u.groupby('acquisition_campaign_id').agg(users=('user_id','size'),kyc=('kyc_completed','sum'),ft=('first_trade_made','sum'))
r=c.set_index('campaign_id')[['acquired_users','kyc_completions','first_traders','campaign_spend_inr']].join(g)
r['d_users']=r.acquired_users-r.users; r['d_kyc']=r.kyc_completions-r.kyc; r['d_ft']=r.first_traders-r.ft
P(r.to_string()); P('total spend',c.campaign_spend_inr.sum(),' paid-user CAC (spend>0):',round(c.campaign_spend_inr.sum()/c.loc[c.campaign_spend_inr>0,'acquired_users'].sum(),1),' blended all users:',round(c.campaign_spend_inr.sum()/c.acquired_users.sum(),1))
P('\n== MONTHLY ACTIVITY LOGIC')
mm=m.merge(u[['user_id','registration_date','first_trade_date','first_deposit_date','first_trade_made','first_deposit_made','last_active_date','kyc_completed']],on='user_id')
mm['mdate']=pd.to_datetime(mm.activity_month+'-01'); mm['reg_m']=pd.to_datetime(mm.registration_date).dt.to_period('M').dt.to_timestamp()
exp=((mm.mdate.dt.year-mm.reg_m.dt.year)*12+mm.mdate.dt.month-mm.reg_m.dt.month)
P('months_since_registration mismatch',(exp!=mm.months_since_registration).sum())
P('rows before registration month',(mm.mdate<mm.reg_m).sum(),' rows after Oct-2026',(mm.activity_month>'2026-10').sum())
expected_rows=sum(((2026-int(x[:4]))*12+10-int(x[5:7]))+1 for x in u.registration_month); P('expected monthly rows',expected_rows,'actual',len(m))
P('trade_count>0 but not active_in_month',((m.trade_count>0)&~m.active_in_month).sum(),' trading_value>0 & trade_count==0',((m.trading_value_inr>0)&(m.trade_count==0)).sum(),' trade_count>0 & value==0',((m.trade_count>0)&(m.trading_value_inr==0)).sum())
P('negative values',(m[['trade_count','trading_value_inr','deposit_value_inr','withdrawal_value_inr']]<0).sum().to_dict())
tm=mm[mm.trade_count>0]
P('trades in months BEFORE the first_trade_date month',(tm.mdate<pd.to_datetime(tm.first_trade_date).dt.to_period('M').dt.to_timestamp()).sum(),'of',len(tm))
P('trades by users with first_trade_made=False',(~tm.first_trade_made).sum())
dm=mm[mm.deposit_value_inr>0]
P('deposit rows',len(dm),' deposits in month before first_deposit month',(dm.mdate<pd.to_datetime(dm.first_deposit_date).dt.to_period('M').dt.to_timestamp()).sum(),' deposit by users with no first deposit',(~dm.first_deposit_made).sum())
wm=mm[mm.withdrawal_value_inr>0]
P('withdrawal rows',len(wm),' withdrawals by users w/o any deposit',(~wm.first_deposit_made).sum(),' withdrawals in months before first deposit',(wm.mdate<pd.to_datetime(wm.first_deposit_date).dt.to_period('M').dt.to_timestamp()).sum())
act=mm[mm.active_in_month]
P('active rows after last_active_date month',(act.mdate>pd.to_datetime(act.last_active_date).dt.to_period('M').dt.to_timestamp()).sum(),'of',len(act))
P('month-0 active rate',m[m.months_since_registration==0].active_in_month.mean().round(4))
P('users active in final month (Oct-26)',m[m.activity_month=='2026-10'].active_in_month.sum(),' vs users active_30d',u.active_30d.sum())
P('users with last_active in Oct-26',(L>='2026-10-01').sum())
P('\n== SUPPORT TICKETS LOGIC')
tt=t.merge(u[['user_id','registration_date']],on='user_id'); 
P('ticket before registration',(pd.to_datetime(tt.created_date)<pd.to_datetime(tt.registration_date)).sum())
P('created_month mismatch',(pd.to_datetime(t.created_date).dt.strftime('%Y-%m')!=t.created_month).sum())
P('status x res_time/csat nulls'); P(t.groupby('status').agg(n=('ticket_id','size'),res_null=('resolution_time_hours',lambda s:s.isna().sum()),csat_null=('csat_score',lambda s:s.isna().sum())).to_string())
P('csat values',t.csat_score.value_counts(dropna=False).sort_index().to_dict(),' res time describe',t.resolution_time_hours.describe().round(2).to_dict())
P('tickets per user max',t.groupby('user_id').size().max(),' users w/ ticket',t.user_id.nunique())
P('tickets before 2025-11? min date',t.created_date.min(),' tickets pre-2026 (users registered 2026-01+ cannot exist pre-Jan?)')
P('\n== COHORT SHEET vs recompute')
mc=m.merge(u[['user_id','registration_month']],on='user_id')
rc=mc.groupby(['registration_month','months_since_registration']).agg(cu=('user_id','nunique'),au=('active_in_month','sum')).reset_index()
cm=co.merge(rc,on=['registration_month','months_since_registration'],how='outer')
P('cohort rows',len(co),'recomputed',len(rc),' mismatch users',(cm.cohort_users!=cm.cu).sum(),' mismatch active',(cm.active_users!=cm.au).sum())
P('Cohort denominator caveat: cohort_users repeated per month; check month-0 cohort_users == signups',co[co.months_since_registration==0].cohort_users.sum())
P('registrations by month',u.registration_month.value_counts().sort_index().to_dict())
P('\n== ORGANIC vs PAID mix, CAMPAIGN spend monthly?', 'spend only as lump-sum per campaign; no monthly spend -> no time-series CAC')
open(ROOT/'01_data_audit'/'phase1_audit_raw_log.txt','w').write('\n'.join(out))
