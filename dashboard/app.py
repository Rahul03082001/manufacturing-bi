"""Read only, one repeatable-read snapshot for every card and chart in a refresh."""
import pandas as pd
import streamlit as st
from sqlalchemy import text
from src.db import engine

st.set_page_config(page_title='Manufacturing BI', page_icon='🏭', layout='wide')
st.title('Manufacturing inventory')
st.caption('COMPONENT OPERATIONS  /  One plant · USD · Individual units · Synthetic data')


def dollars(cents):
    return f'${int(cents)/100:,.2f}'


def display(conn):
    status = conn.execute(text('SELECT * FROM reporting.status')).mappings().one()
    failures = pd.read_sql(text('SELECT * FROM reporting.recent_failures'), conn)
    if status['latest_outcome'] == 'FAILED':
        st.warning('The latest attempt failed validation. Business metrics still show the previous successful version.'
                   if status['published_run_id'] else 'The latest attempt failed validation. No approved business data is available.')
    st.button('Refresh approved data', help='Reload the published snapshot and latest run status.')
    inventory_tab, reconciliation_tab, status_tab = st.tabs(['Inventory', 'Reconciliation', 'Run status'])
    with status_tab:
        left, right = st.columns(2)
        left.markdown('**Published snapshot**')
        left.write(str(status['published_run_id'] or 'None yet'))
        left.caption(f"Published: {status['published_at'] or '—'} (UTC)")
        right.markdown(f"**Latest attempt: {status['latest_outcome'] or 'No attempts'}**")
        right.write(str(status['latest_run_id'] or '—'))
        right.caption(f"Completed: {status['latest_completed_at'] or '—'} (UTC)")
        st.subheader('Recent validation failures')
        if failures.empty:
            st.success('No recorded validation failures.')
        else:
            failures['details'] = failures['details'].map(lambda d: str(d.get('errors', [])))
            st.dataframe(failures.rename(columns={'control':'Control','details':'Details','checked_at':'Checked at (UTC)','run_id':'Run ID'}), use_container_width=True, hide_index=True)
    if not status['published_run_id']:
        with inventory_tab:
            st.info('No approved data yet. Run the clean pipeline to publish the first snapshot.')
        with reconciliation_tab:
            st.info('Reconciliation appears after the first successful publication.')
        return
    run_id = status['published_run_id']
    params = {'run_id': run_id}
    dates = conn.execute(text('SELECT day FROM reporting.daily_summary WHERE run_id=:run_id ORDER BY day'), params).scalars().all()
    items = pd.read_sql(text('SELECT DISTINCT item_id,item_name FROM reporting.inventory WHERE run_id=:run_id ORDER BY item_id'), conn, params=params)
    st.sidebar.header('Inventory filters')
    as_of = st.sidebar.selectbox('As-of date', dates, index=len(dates)-1)
    labels = dict(zip(items.item_id, items.item_name))
    chosen = st.sidebar.multiselect('Components', items.item_id.tolist(), default=items.item_id.tolist(),
                                    format_func=lambda key: f'{key} · {labels[key]}')
    st.sidebar.caption('Reconciliation always covers the whole plant. These component filters apply to Inventory only.')
    params.update({'as_of':as_of, 'items':chosen})
    with inventory_tab:
        st.subheader('Approved inventory')
        st.caption(f'Closing balances at {as_of} · Zero opening stock · Fixed standard costs')
        if not chosen:
            st.info('Select at least one component to explore inventory.')
        else:
            # Filtered business aggregates remain in SQL; Python only formats output.
            summary = conn.execute(text('SELECT sum(inventory_value_cents) AS value,count(*) FILTER(WHERE closing_qty>0) AS positive '
                'FROM reporting.inventory WHERE run_id=:run_id AND day=:as_of AND item_id=ANY(:items)'), params).mappings().one()
            c1,c2 = st.columns(2)
            c1.metric('Closing inventory value', dollars(summary['value']))
            c2.metric('Components with positive stock', int(summary['positive']))
            trend = pd.read_sql(text('SELECT day,sum(inventory_value_cents) AS value_cents FROM reporting.inventory '
                'WHERE run_id=:run_id AND day<=:as_of AND item_id=ANY(:items) GROUP BY day ORDER BY day'), conn, params=params)
            trend['Inventory value (USD)'] = trend.value_cents / 100
            st.area_chart(trend.set_index('day')[['Inventory value (USD)']], color='#167d9a')
            balances = pd.read_sql(text('SELECT item_id,item_name,closing_qty,inventory_value_cents FROM reporting.inventory '
                'WHERE run_id=:run_id AND day=:as_of AND item_id=ANY(:items) ORDER BY inventory_value_cents DESC,item_id'), conn, params=params)
            balances['Value (USD)'] = balances.pop('inventory_value_cents').map(dollars)
            st.dataframe(balances.rename(columns={'item_id':'Component ID','item_name':'Component','closing_qty':'Units on hand'}), hide_index=True, use_container_width=True)
    with reconciliation_tab:
        st.subheader('Inventory ↔ finance')
        st.caption(f'Plant-wide · Account 1400 · As of {as_of} · Component filter does not apply')
        recon = pd.read_sql(text('SELECT day,inventory_value_cents,finance_balance_cents,difference_cents '
                                'FROM reporting.reconciliation WHERE run_id=:run_id ORDER BY day'), conn, params=params)
        selected = recon[recon.day == as_of].iloc[0]
        a,b,c = st.columns(3)
        a.metric('Inventory balance', dollars(selected.inventory_value_cents))
        b.metric('Finance balance', dollars(selected.finance_balance_cents))
        c.metric('Difference', dollars(selected.difference_cents))
        recon['Result'] = recon.difference_cents.map(lambda v:'PASS' if v==0 else 'FAIL')
        for col in ['inventory_value_cents','finance_balance_cents','difference_cents']:
            recon[col] = recon[col].map(dollars)
        st.dataframe(recon.rename(columns={'day':'Date','inventory_value_cents':'Inventory (USD)',
            'finance_balance_cents':'Finance (USD)','difference_cents':'Difference (USD)'}), hide_index=True, use_container_width=True)
    st.caption(f'Approved run {run_id} · Published {status["published_at"]} (UTC)')


reporting_engine = None
try:
    reporting_engine = engine()
    with reporting_engine.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
        with connection.begin():
            connection.execute(text('SET TRANSACTION READ ONLY'))
            display(connection)
except KeyError:
    st.info('The dashboard is waiting for its reporting database settings. The app owner needs to finish the connection setup.')
except Exception:
    st.error('Reporting data is unavailable. Check database health and the reporting account configuration, then refresh.')
finally:
    if reporting_engine is not None:
        reporting_engine.dispose()
