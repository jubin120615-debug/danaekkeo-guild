import streamlit as st
import pandas as pd
from datetime import datetime
import cv2
import easyocr
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 설정 및 인증 ---
st.set_page_config(page_title="다내꺼 길드 관제 센터", layout="wide")

# 구글 시트 연결
creds_dict = st.secrets["gcp_service_account"]
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
client = gspread.authorize(creds)
db = client.open('길드명부')

# --- 2. 데이터 로드 함수 ---
def get_data():
    return {
        "members": pd.DataFrame(db.worksheet("Guild_Data").get_all_records()),
        "notices": db.worksheet("Notice_Board").get_all_records(),
        "raid_logs": db.worksheet("Raid_Logs").get_all_records(),
        "attendance": {row['캐릭터명']: int(row['참여횟수']) for row in db.worksheet("Boss_Stats").get_all_records()}
    }

# 세션 상태 초기화
if "menu" not in st.session_state: st.session_state.menu = "공지사항"
if "is_admin" not in st.session_state: st.session_state.is_admin = False

# --- 3. UI 디자인 (CSS) ---
st.markdown("""<style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #1a1a1a; width: 88px !important; }
    .notice-card { background: #1e1e1e; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #333; }
</style>""", unsafe_allow_html=True)

# --- 4. 사이드바 ---
with st.sidebar:
    if st.button("📢"): st.session_state.menu = "공지사항"
    if st.button("👥"): st.session_state.menu = "명부"
    if st.button("📊"): st.session_state.menu = "참여율"
    if st.button("🔑"): st.session_state.is_admin = not st.session_state.is_admin

# --- 5. 메인 로직 ---
data = get_data()

if st.session_state.menu == "공지사항":
    st.header("📢 공지사항")
    for n in data['notices']:
        st.markdown(f"<div class='notice-card'><b>{n['유형']}</b>: {n['내용']}</div>", unsafe_allow_html=True)

elif st.session_state.menu == "명부":
    st.header("👥 길드 명부")
    edited_df = st.data_editor(data['members'], use_container_width=True)
    if st.session_state.is_admin and st.button("시트 업데이트"):
        ws = db.worksheet("Guild_Data")
        ws.clear()
        ws.update([edited_df.columns.values.tolist()] + edited_df.values.tolist())
        st.success("반영 완료!")

elif st.session_state.menu == "참여율":
    st.header("📊 참여율 정산")
    # 예시: 참여 데이터 표시
    df_att = pd.DataFrame(list(data['attendance'].items()), columns=['캐릭터명', '참여횟수'])
    st.dataframe(df_att)
