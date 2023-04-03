import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from shillelagh.backends.apsw.db import connect

st.set_page_config(
    page_title="簡單ㄉ記帳 App 🧐",
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

# @st.experimental_memo(ttl=600)


def run_query(query):
    return conn.execute(query).fetchall()


def get_data():
    run_query("select * from sheet")


def get_period():
    def get_cur_month():
        return datetime.now().strftime('%Y-%m')

    def get_last_month():
        month_date = datetime.now() - relativedelta(months=1)
        return month_date.strftime('%Y-%m')

    def get_next_month():
        month_date = datetime.now() + relativedelta(months=1)
        return month_date.strftime('%Y-%m')

    today = datetime.today().date()  # 獲取今天的日期
    # date_str = '2023-4-13'
    # today = datetime.strptime(date_str, '%Y-%m-%d').date()

    card_type = st.secrets['card_type']
    period_list = st.secrets['period']
    if len(card_type) != len(period_list):
        assert KeyError(
            f"card_type({len(card_type)})與period({len(period)})數量不一致，")

    period_dict = {}
    for card, period in zip(card_type, period_list):
        if period[0] < period[1]:
            last_month = get_last_month()
            period_dict[card] = [datetime.strptime(f"{last_month}-{period[0]}", "%Y-%m-%d").date(),
                                 datetime.strptime(f"{last_month}-{period[1]}", "%Y-%m-%d").date()]
        else:
            last_month = get_last_month()
            cur_month = get_cur_month()
            period_dict[card] = [datetime.strptime(f"{last_month}-{period[0]}", "%Y-%m-%d").date(),
                                 datetime.strptime(f"{cur_month}-{period[1]}", "%Y-%m-%d").date()]

        # 當超過本月週期，自動移往下個月週期
        if period_dict[card][1] < today:
            for i in range(len(period_dict[card])):
                period_dict[card][i] += relativedelta(months=1)

    return period_dict


def add_row_to_sheet(row: list):
    # 種類	標題	時間	金額	註記	使用者
    column_names = [
        '種類',
        '標題',
        '時間',
        '金額',
        '註記',
        '使用者',
    ]
    sql = f"""
    insert into 
        sheet ("{'", "'.join(column_names)}")
        values ("{'", "'.join(row)}")
    """
    run_query(sql)


def check_password(test_mode=False):
    def password_entered():
        if st.session_state["password"] in st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if not test_mode:
        if "password_correct" not in st.session_state:
            st.text_input(
                "胚斯沃德 🔒",
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
            st.error("密碼錯誤 🤔 別亂來ㄋㄟ")
            return False
        else:
            return st.session_state["password_correct"]
    else:
        return True


# 密碼登入
if check_password(test_mode=False):
    conn = connect_to_gsheet()
    st.title("欸你記ㄍ帳拉")

    period_dict = get_period()  # 獲取信用卡週期

    sidebar = st.sidebar

    # 側邊欄
    with sidebar:
        # sidebar.write("還在測試中喔~")
        sidebar.write(
            f"Google 試算表的[網址](https://docs.google.com/spreadsheets/d/{st.secrets['sheet_id']}/edit)")

        # 欄位說明
        sidebar.write("""
        欄位說明：  
        - `種類`: &nbsp; 信用卡的種類
        - `標題`: &nbsp; 可以理解的標題
        - `時間`: &nbsp; 帳目產生的時間
        - `金額`: &nbsp; 花多少
        - `註記`: &nbsp; 附加說明
        - `使用者`: &nbsp; 誰花的$$
        """)

        # 帳單週期
        sidebar.write('帳單期間：')
        content = ''
        for card in period_dict:
            content += f"- {card}： {period_dict[card][0]}~{period_dict[card][1]}\n"

        sidebar.write(content)

    form = st.form(key="annotation", clear_on_submit=True)

    with form:
        display = {}
        for card in st.secrets["card_type"]:
            display[card] = card

        options = st.secrets["card_type"]

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
            label="金額",
            min_value=0
        )

        comment = st.text_area(label="註記", value="")

        who = st.selectbox(label="誰花ㄉ", options=st.secrets["users"])
        submitted = st.form_submit_button(label="送出")

        if submitted:
            add_row_to_sheet(
                [category, title, date.strftime(
                    "%Y-%m-%d"), str(value), comment, who]
            )
            st.success("新增成功!")
            st.balloons()

    # 取出整個df
        whole_df = pd.read_sql_query("select * from sheet", conn)

    # 顯示本期的紀錄
    expander1 = st.expander("顯示本期紀錄", expanded=True)
    with expander1:
        # 按週期篩選資料
        selected_df = pd.DataFrame()
        for card in period_dict:
            filter_ = (whole_df['種類'] == card) & (whole_df['時間'] >= period_dict[card][0]) & (
                whole_df['時間'] <= period_dict[card][1])
            selected_df = pd.concat(
                [selected_df, whole_df[filter_]], axis=0, ignore_index=True)

        tab1, tab2, tab3 = st.tabs(["卡片", "使用者", "本期總覽"])

        with tab1:  # 卡片
            if len(selected_df) == 0:
                st.write("沒有紀錄，先記帳啦～")

            for col, card_type in zip(st.columns(len(st.secrets["card_type"])), st.secrets["card_type"]):
                sub_df = selected_df[selected_df['種類'] == card_type]
                price = sub_df['金額'].sum()

                col.metric(card_type, f'$ {price}')

                sub_df = sub_df.drop('種類', axis=1).sort_values(
                    by="時間", ascending=True).reset_index(drop=True)
                col.dataframe(sub_df,
                              use_container_width=True)

        with tab2:  # 使用者
            if len(selected_df) == 0:
                st.write("沒有紀錄，先記帳啦～")

            for col, user in zip(st.columns(2), st.secrets["users"]):
                sub_df = selected_df[selected_df['使用者'] == user]
                price = sub_df['金額'].sum()

                col.metric(user, f'$ {price}')

                sub_df = sub_df.drop('使用者', axis=1).sort_values(
                    by="時間", ascending=True).reset_index(drop=True)
                col.dataframe(sub_df,
                              use_container_width=True)

        with tab3:  # 本期總覽
            df = selected_df.sort_values(
                by="時間", ascending=True).reset_index(drop=True)
            st.metric('Total', f"$ {df['金額'].sum()}")
            st.dataframe(df, use_container_width=True)

    # 顯示本月的紀錄
    expander2 = st.expander("顯示本月紀錄", expanded=True)
    with expander2:
        # 取得本月的起始和結束時間
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1).date()
        end_of_month = (datetime(now.year, now.month+1, 1) -
                        pd.Timedelta(days=1)).date()

        # 按週期篩選資料
        filter_ = (whole_df['時間'] >= start_of_month) & (
            whole_df['時間'] <= end_of_month)
        selected_df = whole_df[filter_]
        selected_df = selected_df.reset_index(drop=True)

        tab1, tab2, tab3 = st.tabs(["卡片", "使用者", "本月總覽"])

        with tab1:  # 卡片
            if len(selected_df) == 0:
                st.write("沒有紀錄，先記帳啦～")

            for col, card_type in zip(st.columns(len(st.secrets["card_type"])), st.secrets["card_type"]):
                sub_df = selected_df[selected_df['種類'] == card_type]
                price = sub_df['金額'].sum()

                col.metric(card_type, f'$ {price}')

                sub_df = sub_df.drop('種類', axis=1).sort_values(
                    by="時間", ascending=True).reset_index(drop=True)
                col.dataframe(sub_df,
                              use_container_width=True)

        with tab2:  # 使用者
            if len(selected_df) == 0:
                st.write("沒有紀錄，先記帳啦～")

            for col, user in zip(st.columns(2), st.secrets["users"]):
                sub_df = selected_df[selected_df['使用者'] == user]
                price = sub_df['金額'].sum()

                col.metric(user, f'$ {price}')

                sub_df = sub_df.drop('使用者', axis=1).sort_values(
                    by="時間", ascending=True).reset_index(drop=True)
                col.dataframe(sub_df,
                              use_container_width=True)

        with tab3:  # 本月總覽
            df = selected_df.sort_values(
                by="時間", ascending=True).reset_index(drop=True)
            st.metric('Total', f"$ {df['金額'].sum()}")
            st.dataframe(df, use_container_width=True)

    # 總覽
    expander3 = st.expander("顯示全部紀錄", expanded=True)
    with expander3:
        df = whole_df.sort_values(
            by="時間", ascending=False).reset_index(drop=True)
        st.metric('Total', f"$ {df['金額'].sum()}")
        st.dataframe(df, use_container_width=True)
