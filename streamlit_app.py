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

def check_password():
    def password_entered():
        if st.session_state["password"] in st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    
    if "password_correct" not in st.session_state:
        st.text_input(
            "🔒",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "🔒",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("密碼錯誤 🤔 你有沒有試過你的 Moodle 密碼呢？")
        return False
    else:
        return st.session_state["password_correct"]

if check_password():
    conn = connect_to_gsheet()
    st.title("欸你記ㄍ帳拉")

    sidebar = st.sidebar

    with sidebar:
        sidebar.write("還在測試中喔")
        sidebar.write(
            "Google 試算表的[網址](https://docs.google.com/spreadsheets/d/1z_tAkygIBcAQxlVo7LqQzRQ4FZjGXMFDQOTXFGcPRNo/edit)")
        sidebar.write("欄位說明：")
        sidebar.write("""
        - `種類`: 帳目的種類
        - `標題`: 可以理解的標題
        - `時間`: 帳目產生的時間
        - `元`: 帳目數字
        - `註記`: 附加說明
        - `誰`: $$來源
        """)

    form = st.form(key="annotation", clear_on_submit=True)

    with form:
        display = {
            "食物": '食物 🍙',
            "遊戲": '遊戲 🎮',
            "現金": '竟然直接給錢！？ 💵',
            "其他": '其他東西 ⚒️'
        }
        options = ["食物", "遊戲", "現金", "其他"]

        category = st.selectbox(
            label="種類",
            options=options, format_func=lambda x: display.get(x))

        title = st.text_input(
            label="標題"
        )

        date = st.date_input(
            label="產生日期"
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
                [category, title, date.strftime(
                    "%Y-%m-%d"), str(value), comment, who]
            )
            st.success("新增成功!")
            st.balloons()

    expander = st.expander("顯示目前的紀錄")
    with expander:
        df = pd.read_sql_query("select * from sheet",
                            conn)

        def sumOfVal(series):
            if series.name:
                return series["元"].sum()
            return 0
        df_by_who = df.groupby('誰').apply(sumOfVal)
        df_by_who = pd.DataFrame(df_by_who, columns=["付出的＄"])
        col1, col2 = st.columns(2)
        p1: int = df_by_who.iloc[0]
        p2: int = df_by_who.iloc[1]
        col1.metric(str(df_by_who.index[0]), p2)
        col2.metric(str(df_by_who.index[1]), p1)
        st.dataframe(df.sort_values(by="時間", ascending=False),
                    use_container_width=True)
