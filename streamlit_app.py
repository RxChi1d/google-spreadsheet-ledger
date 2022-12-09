import streamlit as st
import pandas as pd
from shillelagh.backends.apsw.db import connect

st.set_page_config(
    page_title="簡單ㄉ記帳 App🧐",
    page_icon="👀",
    layout="centered"
)


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


def get_data():
    run_query("select * from sheet")


def add_row_to_sheet(row: list):
    # 種類	標題	時間	元	註記	誰
    column_names = [
        '種類',
        '標題',
        '時間',
        '元',
        '註記',
        '誰',
    ]
    sql = f"""
    insert into 
        sheet ("{'", "'.join(column_names)}")
        values ("{'", "'.join(row)}")
    """
    run_query(sql)


st.title("記ㄍ帳")

form = st.form(key="annotation", clear_on_submit=True)

with form:
    display = {
        "食物": '食物 🍙',
        "遊戲": '遊戲 🎮'
    }
    options = ["食物", "遊戲"]

    category = st.selectbox(
        label="種類",
        options=options, format_func=lambda x: display.get(x))

    title = st.text_input(
        label="標題"
    )

    date = st.date_input(
        label="花費日期"
    )

    value = st.number_input(
        label="元",
        min_value=0
    )

    comment = st.text_area(label="註記", value="")

    who = st.selectbox(label="誰寫ㄉ", options=st.secrets["who"])
    submitted = st.form_submit_button(label="送出")

    if submitted:
        add_row_to_sheet(
            [category, title, date.strftime("%Y-%m-%d"), str(value), comment, who]
        )
        st.success("新增成功!")
        st.balloons()

expander = st.expander("顯示目前的紀錄")
with expander:
    st.dataframe(pd.read_sql_query("select * from sheet", conn).sort_values(by="時間", ascending=False))
