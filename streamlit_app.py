import streamlit as st
from shillelagh.backends.apsw.db import connect

@st.experimental_singleton
def connect_to_gsheet():
    gcp = dict(st.secrets["gcp_service_account"])
    return connect(
        ":memory:",
        adapters="gsheetsapi",
        adapter_kwargs={
            "gsheetsapi": {
                "service_account_info": gcp,
                "subject": gcp['client_email'],
                "catalog": {
                    "sheet": f"https://docs.google.com/spreadsheets/d/{st.secrets['sheet_id']}/edit#gid=0"
                }
            },
        }
    )

conn = connect_to_gsheet()

@st.experimental_memo(ttl=600)
def run_query(query):
    return conn.execute(query).fetchall()

rows = run_query("select * from sheet")

for row in rows:
    st.write(f"{row[0]} {row[1]}")

run_query("insert into sheet ('name', 'value') values('D', 4)")
