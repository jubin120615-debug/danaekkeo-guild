import streamlit as st
import pandas as pd
from datetime import datetime
import cv2
import easyocr
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. 페이지 설정
st.set_page_config(page_title="다내꺼 길드 관제 센터", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 구글 시트 연동 함수
# ==========================================
@st.cache_resource
def get_workbook():
    creds_dict = st.secrets["gcp_service_account"]
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)
    return client.open('길드명부')

def get_sheet(tab_name):
    return get_workbook().worksheet(tab_name)

def load_members():
    try:
        data = get_sheet('길드명부').get_all_records()
        if data:
            df = pd.DataFrame(data)
            df["레벨"]   = pd.to_numeric(df["레벨"],   errors="coerce").fillna(1).astype(int)
            df["전투력"] = pd.to_numeric(df["전투력"], errors="coerce").fillna(0).astype(int)
            return df
    except Exception as e:
        st.warning(f"명부 불러오기 실패: {e}")
    return pd.DataFrame([
        {"캐릭터명": "다내꺼마스터", "클래스": "버서커", "레벨": 75, "전투력": 65400, "비고": "총군"},
        {"캐릭터명": "아가사", "클래스": "디바인어벤저", "레벨": 73, "전투력": 61200, "비고": "간부"},
        {"캐릭터명": "전투토끼", "클래스": "엘리멘탈리스트", "레벨": 72, "전투력": 59800, "비고": "-"},
        {"캐릭터명": "태양5_K세이지", "클래스": "레인저", "레벨": 71, "전투력": 58500, "비고": "-"},
        {"캐릭터명": "타양5_K스님", "클래스": "다크프리스트", "레벨": 70, "전투력": 57200, "비고": "-"},
        {"캐릭터명": "타양5_Kangnam", "클래스": "뱅가드", "레벨": 70, "전투력": 56900, "비고": "-"},
        {"캐릭터명": "타양5_K땡벌", "클래스": "버서커", "레벨": 69, "전투력": 55400, "비고": "-"},
    ])

def save_members(df):
    try:
        sh = get_sheet('길드명부')
        sh.clear()
        sh.update([df.columns.tolist()] + df.astype(str).values.tolist())
    except Exception as e:
        st.error(f"명부 저장 실패: {e}")

def load_notices():
    try:
        data = get_sheet('공지사항').get_all_records()
        if data:
            return data
    except Exception as e:
        st.warning(f"공지 불러오기 실패: {e}")
    return [{"id": 1, "유형": "🚫 통제", "내용": "제로서버 주요 보스 구역 및 심연 3층은 전부 '다내꺼' 통제 구역입니다.", "날짜": "2026-06-13 09:00"}]

def save_notices(notices):
    try:
        sh = get_sheet('공지사항')
        sh.clear()
        sh.update([["id", "유형", "내용", "날짜"]] + [[n["id"], n["유형"], n["내용"], n["날짜"]] for n in notices])
    except Exception as e:
        st.error(f"공지 저장 실패: {e}")

def load_attendance():
    try:
        data = get_sheet('참여율').get_all_records()
        if data:
            return {row["캐릭터명"]: int(row["횟수"]) for row in data}
    except Exception as e:
        st.warning(f"참여율 불러오기 실패: {e}")
    return {"다내꺼마스터": 42, "아가사": 38, "전투토끼": 15, "태양5_K세이지": 22, "타양5_K스님": 19, "타양5_Kangnam": 31, "타양5_K땡벌": 8}

def save_attendance(attendance):
    try:
        sh = get_sheet('참여율')
        sh.clear()
        sh.update([["캐릭터명", "횟수"]] + [[k, v] for k, v in attendance.items()])
    except Exception as e:
        st.error(f"참여율 저장 실패: {e}")

def load_raid_logs():
    try:
        data = get_sheet('레이드로그').get_all_records()
        if data:
            logs = {}
            for row in data:
                key = (row["날짜"], row["보스명"])
                if key not in logs:
                    logs[key] = {"날짜": row["날짜"], "보스명": row["보스명"], "참여명단": []}
                if row["캐릭터명"]:
                    logs[key]["참여명단"].append(row["캐릭터명"])
            return list(logs.values())
    except Exception as e:
        st.warning(f"레이드 로그 불러오기 실패: {e}")
    return [
        {"날짜": "2026-06-12", "보스명": "벨루치 (필드)", "참여명단": ["다내꺼마스터", "아가사", "전투토끼", "태양5_K세이지", "타양5_Kangnam"]},
        {"날짜": "2026-06-11", "보스명": "바포메트 (심연)", "참여명단": ["다내꺼마스터", "아가사", "타양5_K스님", "타양5_Kangnam"]}
    ]

def save_raid_logs(logs):
    try:
        sh = get_sheet('레이드로그')
        sh.clear()
        rows = [["날짜", "보스명", "캐릭터명"]]
        for log in logs:
            for char in log["참여명단"]:
                rows.append([log["날짜"], log["보스명"], char])
        sh.update(rows)
    except Exception as e:
        st.error(f"레이드 로그 저장 실패: {e}")

# ✅ 보스목록 시트 연동 함수 (신규 추가)
def load_boss_list():
    try:
        data = get_sheet('보스목록').get_all_records()
        if data:
            return [str(row["보스명"]) for row in data if row["보스명"]]
    except Exception as e:
        st.warning(f"보스목록 불러오기 실패: {e}")
    return ["벨루치 (필드)", "가나비슈 (필드)", "바포메트 (심연)", "라돈 (심연)", "기타 정예"]

def save_boss_list(boss_list):
    try:
        sh = get_sheet('보스목록')
        sh.clear()
        sh.update([["보스명"]] + [[b] for b in boss_list])
    except Exception as e:
        st.error(f"보스목록 저장 실패: {e}")

def load_env_config():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
        client = gspread.authorize(creds)
        wb = client.open('길드명부')
        data = wb.worksheet('환경설정').get_all_records()
        if data:
            cfg = {str(row["키"]): str(row["값"]) for row in data}
            if "admin_password" not in cfg and "password" in cfg:
                cfg["admin_password"] = cfg["password"]
            return cfg
    except Exception as e:
        st.warning(f"환경설정 불러오기 실패: {e}")
    return {}

def save_env_config(discord_url, kakao_url, password):
    try:
        sh = get_sheet('환경설정')
        sh.clear()
        sh.update([
            ["키", "값"],
            ["discord_url", discord_url],
            ["kakao_url", kakao_url],
            ["password", password]
        ])
    except Exception as e:
        st.error(f"환경설정 저장 실패: {e}")

# ==========================================
# 2. 세션 상태 초기화
# ==========================================
if "current_menu" not in st.session_state:
    st.session_state.current_menu = "공지사항"
if "auth_target" not in st.session_state:
    st.session_state.auth_target = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "headers" not in st.session_state:
    st.session_state.headers = {"col1": "캐릭터명", "col2": "클래스", "col3": "레벨", "col4": "전투력", "col5": "비고"}
# ✅ 수정: 시트에서 보스목록 불러오기
if "boss_list" not in st.session_state:
    st.session_state.boss_list = load_boss_list()
if "notices" not in st.session_state:
    st.session_state.notices = load_notices()
if "guild_members" not in st.session_state:
    st.session_state.guild_members = load_members()
if "boss_attendance" not in st.session_state:
    st.session_state.boss_attendance = load_attendance()
if "raid_logs" not in st.session_state:
    st.session_state.raid_logs = load_raid_logs()
if "ocr_done" not in st.session_state:
    st.session_state.ocr_done = False
if "detected_cache" not in st.session_state:
    st.session_state.detected_cache = []

_cfg = load_env_config()
if "discord_url" not in st.session_state:
    st.session_state.discord_url = _cfg.get("discord_url", "https://discord.com/")
if "kakao_url" not in st.session_state:
    st.session_state.kakao_url = _cfg.get("kakao_url", "https://open.kakao.com/")
st.session_state.admin_password = _cfg.get("admin_password", "1336")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['ko', 'en'], gpu=False)

# ==========================================
# 3. CSS 스타일
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #121212 !important;
        color: #e0e0e0 !important;
        font-family: 'Noto Sans KR', sans-serif;
    }
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
    [data-testid="stSidebar"] {
        min-width: 230px !important; max-width: 230px !important;
        background-color: #1a1a1a !important;
        border-right: 1px solid #2d2d2d !important;
    }
    [data-testid="stSidebarUserContent"] {
        padding: 20px 14px !important;
    }
    [data-testid="stSidebarUserContent"] div.stButton > button {
        width: 100% !important;
        min-height: 46px !important;
        border-radius: 10px !important;
        border: 1px solid transparent !important;
        background-color: transparent !important;
        color: #aaaaaa !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 0 14px !important;
        margin: 3px 0 !important;
        line-height: 1.2 !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stSidebarUserContent"] div.stButton > button p {
        text-align: left !important;
        font-size: 0.95rem !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
    }
    [data-testid="stSidebarUserContent"] div.stButton > button:hover {
        background-color: #232428 !important;
        color: #00e676 !important;
        border-color: #2d3035 !important;
    }
    [data-testid="stSidebarUserContent"] div.stButton > button[kind="primary"] {
        background-color: rgba(0, 230, 118, 0.12) !important;
        color: #00e676 !important;
        border: 1px solid rgba(0, 230, 118, 0.35) !important;
    }
    [data-testid="stSidebarUserContent"] div.stButton > button[kind="primary"]:hover {
        background-color: rgba(0, 230, 118, 0.18) !important;
    }
    .sidebar-divider { width: 100%; height: 1px; background-color: #2d2d2d; margin: 12px 0; }
    .sidebar-link-btn {
        display: flex; align-items: center; gap: 12px;
        width: 100%; min-height: 46px; box-sizing: border-box;
        border-radius: 10px; background-color: transparent;
        border: 1px solid transparent; color: #aaaaaa !important;
        font-size: 0.95rem; font-weight: 500;
        text-decoration: none !important; padding: 0 14px;
        transition: all 0.2s ease; margin: 3px 0;
    }
    .sidebar-link-btn:visited { color: #aaaaaa !important; }
    .sidebar-link-btn:hover {
        border-color: #2d3035 !important; color: #00e676 !important;
        background-color: #232428 !important;
        text-decoration: none !important;
    }
    .sidebar-icon {
        display: inline-flex; align-items: center; justify-content: center;
        width: 22px; flex-shrink: 0;
    }
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined';
        font-weight: normal; font-style: normal;
        font-size: 20px; line-height: 1;
        letter-spacing: normal; text-transform: none;
        white-space: nowrap; direction: ltr;
        -webkit-font-smoothing: antialiased;
    }
    [data-testid="stIconMaterial"] {
        font-size: 20px !important;
        width: 22px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex-shrink: 0 !important;
    }
    .auth-box {
        background-color: #1a1a1a; border: 1px solid #333333; border-radius: 16px;
        padding: 40px; max-width: 500px; margin: 80px auto; text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    }
    .notice-card {
        background-color: #1e1e1e; padding: 24px; border-radius: 12px;
        border: 1px solid #2d2d2d; margin-bottom: 16px;
    }
    .badge {
        background-color: #2d2d2d; color: #00e676; padding: 6px 12px;
        border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-right: 12px;
    }
    .stat-card {
        background-color: #1a1a1a; border: 1px solid #2d2d2d;
        border-radius: 12px; padding: 20px; text-align: center;
    }
    .stat-number { color: #00e676; font-size: 2rem; font-weight: bold; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. 사이드바
# ==========================================
with st.sidebar:
    # 상단 로고 + 타이틀
    st.markdown("""
    <div style="display:flex; align-items:center; gap:10px; padding: 4px 4px 18px 4px;">
        <div style="width: 38px; height: 38px; background: linear-gradient(135deg, #00e676, #00b0ff);
                    border-radius: 10px; display:flex; align-items:center; justify-content:center;
                    font-weight:bold; color:#121212; font-size:0.75rem;
                    box-shadow: 0 4px 12px rgba(0, 230, 118, 0.35);">채채TV</div>
        <div style="color:#e0e0e0; font-size:1.15rem; font-weight:bold;">레이븐2 <br> 다내꺼</div>
    </div>
    <div class="sidebar-divider"></div>
    """, unsafe_allow_html=True)

    # 메인 메뉴
    menu_items = [
        ("공지사항", "campaign", "공지사항"),
        ("명부", "group", "길드원 명부"),
        ("참여율", "bar_chart", "보스 참여 기록"),
        ("로그", "history_edu", "레이드 로그"),
    ]
    for menu_key, menu_icon, menu_text in menu_items:
        is_active = (st.session_state.auth_target is None) and (st.session_state.current_menu == menu_key)
        if st.button(f":material/{menu_icon}: {menu_text}", key=f"side_{menu_key}", use_container_width=True,
                      type="primary" if is_active else "secondary"):
            st.session_state.current_menu = menu_key
            st.session_state.auth_target = None
            st.rerun()

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # 외부 링크
    st.markdown(
        f'<a href="{st.session_state.discord_url}" target="_blank" class="sidebar-link-btn">'
        f'<span class="material-symbols-outlined sidebar-icon">sports_esports</span><span>디스코드 채널</span></a>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<a href="{st.session_state.kakao_url}" target="_blank" class="sidebar-link-btn">'
        f'<span class="material-symbols-outlined sidebar-icon">chat</span><span>카카오톡방</span></a>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # 관리자 / 환경설정
    admin_icon = "shield_person" if st.session_state.is_admin else "key"
    admin_text = "관리자 모드 ON" if st.session_state.is_admin else "관리자 모드"
    if st.button(f":material/{admin_icon}: {admin_text}", key="side_admin_mode", use_container_width=True,
                  type="primary" if st.session_state.is_admin else "secondary"):
        if st.session_state.is_admin:
            st.session_state.is_admin = False
            st.toast("🛡️ 관리자 권한이 안전하게 해제되었습니다.")
        else:
            st.session_state.auth_target = "admin"
        st.rerun()

    config_active = (st.session_state.auth_target == "config") or (st.session_state.current_menu == "환경설정")
    if st.button(":material/settings: 마스터 환경설정", key="side_config_mode", use_container_width=True,
                  type="primary" if config_active else "secondary"):
        st.session_state.auth_target = "config"
        st.rerun()

# ==========================================
# 5. 비밀번호 인증
# ==========================================
if st.session_state.auth_target is not None:
    target_name = "👑 간부 관리자 권한" if st.session_state.auth_target == "admin" else "⚙️ 관제 센터 마스터 설정"
    st.markdown(f"""
    <div class="auth-box">
        <h2 style="color: #00e676; margin-bottom: 5px;">🔒 보안 인증</h2>
        <p style="color: #888888; font-size: 0.95rem;">{target_name} 진입을 위한 비밀번호를 기입하세요.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("isolated_password_form", clear_on_submit=True):
        input_pwd = st.text_input("PASSWORD INPUT", type="password", label_visibility="collapsed", placeholder="비밀번호를 입력하세요...")
        c_sub, c_esc = st.columns(2)
        btn_login = c_sub.form_submit_button("🔓 인증 및 로그인", use_container_width=True)
        btn_cancel = c_esc.form_submit_button("↩️ 돌아가기", use_container_width=True)

        if btn_login:
            if input_pwd == st.session_state.admin_password:
                if st.session_state.auth_target == "admin":
                    st.session_state.is_admin = True
                    st.session_state.auth_target = None
                elif st.session_state.auth_target == "config":
                    st.session_state.is_admin = True
                    st.session_state.current_menu = "환경설정"
                    st.session_state.auth_target = None
                st.rerun()
            else:
                st.error("❌ 비밀번호가 다릅니다. 다시 확인해 주세요.")
        if btn_cancel:
            st.session_state.auth_target = None
            st.rerun()

else:
    if st.session_state.is_admin:
        st.markdown('<div style="text-align: right; color: #00e676; font-size: 0.85rem; font-weight: bold; padding-right: 10px;">🛡️ 간부 관리 모드 가동 중</div>', unsafe_allow_html=True)

    st.markdown(f'<div style="color: #00e676; font-size: 2.3rem; font-weight: bold; margin-bottom: 2px;">{st.session_state.current_menu}</div>', unsafe_allow_html=True)
    st.caption(f"다내꺼 관제 대시보드 > {st.session_state.current_menu}")
    st.markdown("<hr style='border-color:#2d2d2d;'>", unsafe_allow_html=True)

    # ==========================================
    # 환경설정
    # ==========================================
    if st.session_state.current_menu == "환경설정":
        st.subheader("⚙️ 마스터 시스템 환경설정")
        st.info("디스코드, 카카오톡 주소 및 진입 패스워드를 통합 제어하는 전용 제어반입니다.")
        with st.form("dashboard_config_form"):
            st.markdown("#### 1. 커뮤니티 다이렉트 연동 링크 수정")
            new_discord = st.text_input("🎮 디스코드 접속 링크", value=st.session_state.discord_url)
            new_kakao = st.text_input("💬 카카오톡 단톡방 링크", value=st.session_state.kakao_url)
            st.markdown("---")
            st.markdown("#### 2. 통합 관제 게이트웨이 보안 암호 수정")
            new_password = st.text_input("🔒 신규 마스터 비밀번호 설정", value=st.session_state.admin_password, type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            save_config_btn = st.form_submit_button("💾 설정 변경 사항 일괄 저장")
            if save_config_btn:
                st.session_state.discord_url = new_discord
                st.session_state.kakao_url = new_kakao
                st.session_state.admin_password = new_password
                save_env_config(new_discord, new_kakao, new_password)
                st.cache_resource.clear()
                st.success("🔥 환경설정이 저장되었습니다! 새로고침해도 유지됩니다.")
                st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↩️ 일반 모드로 안전 복귀"):
            st.session_state.is_admin = False
            st.session_state.current_menu = "공지사항"
            st.rerun()

    # ==========================================
    # 공지사항
    # ==========================================
    elif st.session_state.current_menu == "공지사항":
        if st.session_state.is_admin:
            with st.expander("📝 [간부 전용] 새 공지사항 강제 등록", expanded=True):
                with st.form("new_notice_form", clear_on_submit=True):
                    c_type, _ = st.columns([1, 1])
                    notice_type = c_type.selectbox("공지 유형", ["🚫 통제", "📢 일반", "🔥 긴급", "⚔️ 레이드"])
                    notice_content = st.text_area("공지 내용", placeholder="공지할 내용을 상세히 입력하세요.")
                    submit_notice = st.form_submit_button("💾 공지 등록")
                    if submit_notice:
                        if notice_content.strip():
                            new_id = len(st.session_state.notices) + 1
                            now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                            new_notice = {"id": new_id, "유형": notice_type, "내용": notice_content, "날짜": now_str}
                            st.session_state.notices.insert(0, new_notice)
                            save_notices(st.session_state.notices)
                            st.success("✅ 공지사항이 등록되었습니다!")
                            st.rerun()
                        else:
                            st.error("내용을 정확히 입력해주세요.")
            st.markdown("<br>", unsafe_allow_html=True)

        for notice in st.session_state.notices:
            st.markdown(f"""
            <div class="notice-card">
                <span class="badge">{notice['유형']}</span> <small style="color:#777">⏰ {notice['날짜']}</small>
                <p style="margin-top:10px; font-size: 1.05rem; line-height: 1.6;">{notice['내용']}</p>
            </div>
            """, unsafe_allow_html=True)

    # ==========================================
    # 명부
    # ==========================================
    elif st.session_state.current_menu == "명부":
        st.subheader("👥 길드 명부 및 전투력 순위")

        if st.session_state.is_admin:
            with st.expander("🛠️ 표 상단 타이틀 명칭 수정", expanded=False):
                c1, c2, c3, c4, c5 = st.columns(5)
                st.session_state.headers["col1"] = c1.text_input("1번 칸", value=st.session_state.headers["col1"])
                st.session_state.headers["col2"] = c2.text_input("2번 칸", value=st.session_state.headers["col2"])
                st.session_state.headers["col3"] = c3.text_input("3번 칸", value=st.session_state.headers["col3"])
                st.session_state.headers["col4"] = c4.text_input("4번 칸", value=st.session_state.headers["col4"])
                st.session_state.headers["col5"] = c5.text_input("5번 칸", value=st.session_state.headers["col5"])

            with st.expander("➕ 새 길드원 추가", expanded=False):
                with st.form("add_member_form", clear_on_submit=True):
                    a1, a2, a3, a4, a5 = st.columns(5)
                    new_name  = a1.text_input(st.session_state.headers["col1"])
                    new_class = a2.selectbox(st.session_state.headers["col2"], ["버서커", "디바인어벤저", "엘리멘탈리스트", "레인저", "뱅가드", "다크프리스트"])
                    new_level = a3.number_input(st.session_state.headers["col3"], min_value=1, value=1, step=1)
                    new_power = a4.number_input(st.session_state.headers["col4"], min_value=0, value=0, step=100)
                    new_note  = a5.text_input(st.session_state.headers["col5"])
                    if st.form_submit_button("➕ 추가", use_container_width=True):
                        if new_name.strip():
                            new_row = pd.DataFrame([{"캐릭터명": new_name, "클래스": new_class, "레벨": int(new_level), "전투력": int(new_power), "비고": new_note}])
                            st.session_state.guild_members = pd.concat([st.session_state.guild_members, new_row], ignore_index=True)
                            st.session_state.guild_members["레벨"]   = pd.to_numeric(st.session_state.guild_members["레벨"],   errors="coerce").fillna(1).astype(int)
                            st.session_state.guild_members["전투력"] = pd.to_numeric(st.session_state.guild_members["전투력"], errors="coerce").fillna(0).astype(int)
                            save_members(st.session_state.guild_members)
                            st.toast("✅ 새 길드원이 추가되었습니다.")
                            st.rerun()
                        else:
                            st.error("캐릭터명을 입력해주세요.")

        sorted_members = st.session_state.guild_members.sort_values(by="전투력", ascending=False).reset_index(drop=True)
        class_options = ["버서커", "디바인어벤저", "엘리멘탈리스트", "레인저", "뱅가드", "다크프리스트"]

        h1, h2, h3, h4, h5, h6 = st.columns([2.5, 2, 1, 1.5, 1.5, 1])
        for col, label in zip([h1, h2, h3, h4, h5], [
            st.session_state.headers["col1"], st.session_state.headers["col2"],
            st.session_state.headers["col3"], st.session_state.headers["col4"],
            st.session_state.headers["col5"]
        ]):
            col.markdown(f"<div style='color:#00e676; font-weight:bold; font-size:0.85rem; padding:4px 0;'>{label}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#2d2d2d; margin:4px 0 8px 0;'>", unsafe_allow_html=True)

        for i, row in sorted_members.iterrows():
            if st.session_state.is_admin:
                with st.form(f"edit_row_{i}"):
                    c1, c2, c3, c4, c5, c6 = st.columns([2.5, 2, 1, 1.5, 1.5, 1])
                    e_name  = c1.text_input("이름",    value=str(row["캐릭터명"]), label_visibility="collapsed", key=f"n_{i}")
                    e_class = c2.selectbox("클래스", class_options, index=class_options.index(row["클래스"]) if row["클래스"] in class_options else 0, label_visibility="collapsed", key=f"c_{i}")
                    e_level = c3.number_input("레벨",   value=int(row["레벨"]),    min_value=1,  step=1,   label_visibility="collapsed", key=f"l_{i}")
                    e_power = c4.number_input("전투력", value=int(row["전투력"]),  min_value=0,  step=100, label_visibility="collapsed", key=f"p_{i}")
                    e_note  = c5.text_input("비고",    value=str(row["비고"]),    label_visibility="collapsed", key=f"note_{i}")
                    col_save, col_del = c6.columns(2)
                    btn_save = col_save.form_submit_button("💾")
                    btn_del  = col_del.form_submit_button("🗑️")

                    if btn_save:
                        mask = st.session_state.guild_members["캐릭터명"] == row["캐릭터명"]
                        st.session_state.guild_members.loc[mask, "캐릭터명"] = e_name
                        st.session_state.guild_members.loc[mask, "클래스"]   = e_class
                        st.session_state.guild_members.loc[mask, "레벨"]     = int(e_level)
                        st.session_state.guild_members.loc[mask, "전투력"]   = int(e_power)
                        st.session_state.guild_members.loc[mask, "비고"]     = e_note
                        st.session_state.guild_members["레벨"]   = pd.to_numeric(st.session_state.guild_members["레벨"],   errors="coerce").fillna(1).astype(int)
                        st.session_state.guild_members["전투력"] = pd.to_numeric(st.session_state.guild_members["전투력"], errors="coerce").fillna(0).astype(int)
                        save_members(st.session_state.guild_members)
                        st.toast(f"✅ {e_name} 저장 완료")
                        st.rerun()

                    if btn_del:
                        st.session_state.guild_members = st.session_state.guild_members[
                            st.session_state.guild_members["캐릭터명"] != row["캐릭터명"]
                        ].reset_index(drop=True)
                        save_members(st.session_state.guild_members)
                        st.toast(f"🗑️ {row['캐릭터명']} 삭제 완료")
                        st.rerun()
            else:
                c1, c2, c3, c4, c5, c6 = st.columns([2.5, 2, 1, 1.5, 1.5, 1])
                c1.markdown(f"<div style='padding:10px 0;'>{row['캐릭터명']}</div>", unsafe_allow_html=True)
                c2.markdown(f"<div style='padding:10px 0; color:#aaa;'>{row['클래스']}</div>", unsafe_allow_html=True)
                c3.markdown(f"<div style='padding:10px 0; color:#aaa;'>{int(row['레벨'])}</div>", unsafe_allow_html=True)
                c4.markdown(f"<div style='padding:10px 0; color:#00e676; font-weight:bold;'>{int(row['전투력']):,}</div>", unsafe_allow_html=True)
                c5.markdown(f"<div style='padding:10px 0; color:#aaa;'>{row['비고']}</div>", unsafe_allow_html=True)
                st.markdown("<div style='border-bottom:1px solid #2d2d2d; margin:2px 0;'></div>", unsafe_allow_html=True)

    # ==========================================
    # 참여율
    # ==========================================
    elif st.session_state.current_menu == "참여율":
        if st.session_state.is_admin:

            # ✅ 신규: 보스 목록 관리 UI
            with st.expander("⚔️ 보스 목록 관리 (추가 / 삭제)", expanded=False):
                st.markdown("#### 현재 등록된 보스 목록")
                for b_idx, b_name in enumerate(st.session_state.boss_list):
                    col_name, col_del = st.columns([5, 1])
                    col_name.markdown(f"<div style='padding:8px 0; color:#e0e0e0;'>⚔️ {b_name}</div>", unsafe_allow_html=True)
                    if col_del.button("🗑️", key=f"del_boss_{b_idx}", help=f"{b_name} 삭제"):
                        st.session_state.boss_list.pop(b_idx)
                        save_boss_list(st.session_state.boss_list)
                        st.toast(f"🗑️ '{b_name}' 삭제 완료")
                        st.rerun()

                st.markdown("---")
                st.markdown("#### 새 보스 추가")
                with st.form("add_boss_form", clear_on_submit=True):
                    new_boss_name = st.text_input("보스명 입력", placeholder="예: 케르베로스 (심연)")
                    if st.form_submit_button("➕ 보스 추가", use_container_width=True):
                        if new_boss_name.strip():
                            if new_boss_name.strip() in st.session_state.boss_list:
                                st.warning("이미 등록된 보스명입니다.")
                            else:
                                st.session_state.boss_list.append(new_boss_name.strip())
                                save_boss_list(st.session_state.boss_list)
                                st.toast(f"✅ '{new_boss_name.strip()}' 추가 완료!")
                                st.rerun()
                        else:
                            st.error("보스명을 입력해주세요.")

            st.markdown("### 🛠️ 레이드 출석 체크 입력 패널")
            c_date, c_boss = st.columns(2)
            raid_date = c_date.date_input("레이드 진행 날짜", datetime.now()).strftime('%Y-%m-%d')
            boss_name = c_boss.selectbox("보스 몬스터 선택", st.session_state.boss_list)

            all_characters = [str(c) for c in st.session_state.guild_members["캐릭터명"].tolist() if c and str(c).strip()]
            for char in all_characters:
                if char not in st.session_state.boss_attendance:
                    st.session_state.boss_attendance[char] = 0

            input_method = st.radio("입력 방식을 선택하세요", ["📸 AI 스크린샷 인식 기입", "✍️ 명단에서 멀티 선택"], horizontal=True)
            final_selected_chars = []

            if input_method == "📸 AI 스크린샷 인식 기입":
                uploaded_file = st.file_uploader("스크린샷 업로드", type=["png", "jpg", "jpeg"])
                if uploaded_file is not None:
                    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                    image = cv2.imdecode(file_bytes, 1)
                    st.image(image, caption="업로드된 스크린샷", channels="BGR", width=400)
                    if st.button("🔍 AI 분석 시작"):
                        with st.spinner("OCR 분석 중..."):
                            try:
                                ocr_results = load_ocr_reader().readtext(image)
                                extracted_text = []
                                for res in ocr_results:
                                    try:
                                        if res and len(res) > 1:
                                            extracted_text.append(str(res[1]).strip())
                                    except Exception:
                                        continue
                                detected = []
                                for m in all_characters:
                                    try:
                                        if any(str(m) in t for t in extracted_text):
                                            detected.append(m)
                                    except Exception:
                                        continue
                                st.session_state.detected_cache = detected
                                st.session_state.ocr_done = True
                                st.rerun()
                            except Exception as e:
                                st.error(f"OCR 분석 실패: {e}")

                if st.session_state.ocr_done:
                    found_list = st.session_state.detected_cache
                    missing_list = [m for m in all_characters if m not in found_list]
                    cf, cm = st.columns(2)
                    cf.success(f"✅ 인식 ({len(found_list)}명): " + (", ".join(found_list) if found_list else "없음"))
                    cm.warning(f"⚠️ 미인식 ({len(missing_list)}명): " + (", ".join(missing_list) if missing_list else "없음"))
                    st.markdown("#### ✏️ 최종 참여 명단 확인 및 수정")
                    final_selected_chars = st.multiselect(
                        "참여 인원 (OCR 결과 기반, 수정 가능)",
                        options=all_characters,
                        default=[c for c in found_list if c in all_characters],
                        key="ocr_multiselect"
                    )
            else:
                st.markdown("#### ✅ 참여 인원 선택")
                final_selected_chars = st.multiselect(
                    "참여한 길드원을 선택하세요",
                    options=all_characters,
                    default=[],
                    key="manual_multiselect"
                )
                if final_selected_chars:
                    st.info(f"선택된 인원 {len(final_selected_chars)}명: " + ", ".join(final_selected_chars))

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 참여 인원 등록 및 로그 저장", use_container_width=True):
                if final_selected_chars:
                    for char in final_selected_chars:
                        st.session_state.boss_attendance[char] = st.session_state.boss_attendance.get(char, 0) + 1
                    st.session_state.raid_logs.append({
                        "날짜": raid_date,
                        "보스명": boss_name,
                        "참여명단": final_selected_chars
                    })
                    save_attendance(st.session_state.boss_attendance)
                    save_raid_logs(st.session_state.raid_logs)
                    st.success(f"🔥 {boss_name} 레이드 정산 완료! ({len(final_selected_chars)}명 등록)")
                    st.session_state.ocr_done = False
                    st.session_state.detected_cache = []
                    st.rerun()
                else:
                    st.warning("⚠️ 참여 인원을 1명 이상 선택해주세요.")

            st.markdown("---")

        st.markdown("### 📊 연합 보스 레이드 누적 참여 순위")
        all_characters = [str(c) for c in st.session_state.guild_members["캐릭터명"].tolist() if c and str(c).strip()]
        stat_rows = [{"캐릭터명": char, "누적 참여 횟수": st.session_state.boss_attendance.get(char, 0)} for char in all_characters]
        df_stat = pd.DataFrame(stat_rows).sort_values(by="누적 참여 횟수", ascending=False)

        c_tot, c_top = st.columns(2)
        with c_tot:
            st.markdown(f'<div class="stat-card"><span style="color: #888;">👑 최고 참여 명예의 전당</span><div class="stat-number">{df_stat.iloc[0]["캐릭터명"] if not df_stat.empty else "-"}</div></div>', unsafe_allow_html=True)
        with c_top:
            st.markdown(f'<div class="stat-card"><span style="color: #888;">🔥 최고 레이드 참여 기록</span><div class="stat-number">{df_stat.iloc[0]["누적 참여 횟수"] if not df_stat.empty else 0} 회</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df_stat, use_container_width=True, hide_index=True, column_config={
            "누적 참여 횟수": st.column_config.ProgressColumn("🏅 누적 참여율 (포인트)", min_value=0, max_value=100, format="%d 회")
        })

    # ==========================================
    # 로그
    # ==========================================
    elif st.session_state.current_menu == "로그":
        st.subheader("📜 레이드 정산 히스토리 로그")
        if st.session_state.raid_logs:
            summary_rows = [{"인덱스": idx, "📅 레이드 일자": log["날짜"], "⚔️ 정산 보스": log["보스명"], "👥 총 참여 인원수": f"{len(log['참여명단'])} 명"} for idx, log in enumerate(st.session_state.raid_logs)]
            df_summary = pd.DataFrame(summary_rows).sort_values(by="📅 레이드 일자", ascending=False)
            st.dataframe(df_summary, use_container_width=True, hide_index=True, column_config={"인덱스": None})
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🔍 개별 레이드 명단 상세보기")
            log_options = [f"[{log['날짜']}] {log['보스명']} (총 {len(log['참여명단'])}명)" for log in st.session_state.raid_logs]
            selected_log_title = st.selectbox("참여 명단을 조회할 레이드를 선택하세요", log_options)
            selected_idx = log_options.index(selected_log_title)
            target_log = st.session_state.raid_logs[selected_idx]
            st.markdown(f"**🎯 `{target_log['보스명']}` 참여 명단 현황**")
            member_cols = st.columns(5)
            for m_idx, m_name in enumerate(target_log["참여명단"]):
                with member_cols[m_idx % 5]:
                    st.markdown(f"• `{m_name}`")
        else:
            st.info("아직 등록된 레이드 로그가 없습니다.")
