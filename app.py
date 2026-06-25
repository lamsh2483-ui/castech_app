# Force Streamlit Cloud reload trigger - 2026-06-24-15:34
import streamlit as st
import pandas as pd
import numpy as np
import cv2
from PIL import Image
import os
from datetime import datetime
import database
import urllib.parse
from fpdf import FPDF

# st.dialog 지원 여부에 따른 안전한 데코레이터 정의
if hasattr(st, "dialog"):
    @st.dialog("사진 크게 보기", width="large")
    def show_large_image(image_path):
        st.image(image_path, use_container_width=True)
else:
    # st.dialog이 없는 구버전 Streamlit을 위한 대체 함수
    def show_large_image(image_path):
        st.warning("이 버전의 Streamlit에서는 모달 팝업 크게 보기가 지원되지 않습니다. 아래 이미지를 확인하세요.")
        st.image(image_path, use_container_width=True)

# PDF 보고서 생성 헬퍼 함수 정의
def generate_pdf_report(client_name, start_date_str, end_date_str, selected_eq_str, histories):
    pdf = FPDF()
    pdf.add_page()
    
    # Register font for Korean Unicode support (check local packaged font first)
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/malgun.ttf"
    pdf.add_font("Malgun", "", font_path)
    pdf.set_font("Malgun", size=16)
    
    # Title
    pdf.cell(w=0, h=10, text="🔧 수리/점검 내역 보고서", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    # Metadata info card
    pdf.set_font("Malgun", size=10)
    pdf.cell(w=0, h=6, text=f"• 거래처명: {client_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(w=0, h=6, text=f"• 조회기간: {start_date_str} ~ {end_date_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(w=0, h=6, text=f"• 조회대상: {selected_eq_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(w=0, h=6, text=f"• 총 점검 건수: {len(histories)}건", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(w=0, h=6, text=f"• 보고서 출력일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    # Table Header
    pdf.set_font("Malgun", size=9)
    col_widths = [10, 22, 22, 16, 40, 80]
    headers = ["No", "날짜", "계기 ID", "작업자", "증상 및 상태", "조치 및 수리내용"]
    
    # Draw headers with borders
    for w, header in zip(col_widths, headers):
        pdf.cell(w=w, h=8, text=header, border=1, align="C")
    pdf.ln()
    
    # Table Rows
    pdf.set_font("Malgun", size=8)
    for idx, h in enumerate(histories, 1):
        dt = (h.get("날짜_시간") or "")[:10]
        eq_id = h.get("설비ID") or ""
        worker = h.get("작업자명") or ""
        symptom = h.get("증상상태") or ""
        action = h.get("조치_및_수리내용") or ""
        
        # Clean string values to prevent formatting issues in FPDF
        symptom = symptom.replace("\n", " ").strip()
        action = action.replace("\n", " ").strip()
        
        # Clip strings to fit cells nicely
        if len(symptom) > 20:
            symptom = symptom[:18] + ".."
        if len(action) > 42:
            action = action[:40] + ".."
            
        row_vals = [str(idx), dt, eq_id, worker, symptom, action]
        for w, val in zip(col_widths, row_vals):
            pdf.cell(w=w, h=8, text=val, border=1)
        pdf.ln()
        
    # Footer signature
    pdf.ln(15)
    pdf.set_font("Malgun", size=11)
    pdf.cell(w=0, h=10, text="카스테크 (CAS-TECH) 기술팀", new_x="LMARGIN", new_y="NEXT", align="R")
    
    return bytes(pdf.output())

# 1. 페이지 초기 설정 및 DB 생성
st.set_page_config(
    page_title="카스테크(CAS-TECH) 현장 점검 관리",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 데이터베이스 파일이 없는 경우 마이그레이션 실행
if not os.path.exists(database.DB_FILE):
    database.init_db()

# 세션 시작 시 GitHub 원격지에서 최신 DB 가져옴
if "db_pulled" not in st.session_state:
    try:
        database.sync_pull_from_github()
    except Exception:
        pass
    st.session_state.db_pulled = True

# 사진 저장용 폴더 생성
PHOTOS_DIR = "photos"
if not os.path.exists(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR)

# 2. CSS 스타일 적용 (밝은 산업용 UI - 깔끔하고 고급스러운 테두리 및 호버 효과)
def inject_custom_css():
    st.markdown("""
    <style>
    /* 기본 배경색 및 글꼴 설정 */
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Hide Streamlit top bar (deploy button and three dots menu) */
    [data-testid="stHeader"], 
    header[data-testid="stHeader"], 
    .stAppDeployButton, 
    #MainMenu, 
    footer,
    header {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }
    div[data-testid="stAppViewContainer"] {
        padding-top: 0px !important;
    }
    
    /* 헤더 스타일 */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 15px 10px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
        border: 1px solid #2563eb;
    }
    .main-header h1 {
        margin: 0;
        font-size: 18px !important; /* 모바일 대응 글씨 크기 축소 */
        font-weight: 800;
        letter-spacing: -0.5px;
        color: white !important;
        white-space: nowrap; /* 줄바꿈 방지 */
    }
    @media (min-width: 768px) {
        .main-header {
            padding: 20px;
        }
        .main-header h1 {
            font-size: 26px !important;
        }
    }
    
    /* 고급스러운 디스플레이 창 / 카드 스타일 */
    .lux-card {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: all 0.3s ease;
    }
    .lux-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
        border-color: #3b82f6;
    }
    
    /* 서브 타이틀 및 테두리 */
    .section-title {
        font-size: 18px;
        font-weight: 700;
        color: #1e3a8a;
        border-left: 4px solid #3b82f6;
        padding-left: 10px;
        margin-bottom: 15px;
    }
    
    /* 모든 버튼 스타일 통일 및 호버 효과 (Streamlit data-testid 대응) */
    div[data-testid="stButton"], 
    div[data-testid="element-container"]:has(button[data-testid^="stBaseButton"]) {
        width: 100% !important;
        display: block !important;
    }
    div[data-testid="stButton"] button, 
    button[data-testid^="stBaseButton"] {
        width: 100% !important;
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: white !important;
        color: #1e293b !important;
        font-weight: 600 !important;
        padding: 10px 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-align: center !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    div[data-testid="stButton"] button:hover, 
    button[data-testid^="stBaseButton"]:hover {
        border-color: #3b82f6 !important;
        background-color: #eff6ff !important;
        color: #2563eb !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.15) !important;
    }
    div[data-testid="stButton"] button:active, 
    button[data-testid^="stBaseButton"]:active {
        transform: translateY(1px) !important;
    }
    
    /* 입력 폼 및 선택창 스타일 */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: white !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
    }
    
    /* 거래처 카드 스타일 (그리드 배치용) */
    .client-card-btn {
        background-color: white;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 25px 15px;
        text-align: center;
        cursor: pointer;
        transition: all 0.25s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .client-card-btn:hover {
        border-color: #3b82f6;
        background-color: #f0f6ff;
        transform: scale(1.03);
        box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.1);
    }
    
    /* 점검 이력 리스트 스타일 */
    .history-item {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        position: relative;
    }
    .history-header {
        display: flex;
        justify-content: space-between;
        font-size: 14px;
        color: #64748b;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 5px;
        margin-bottom: 8px;
    }
    .history-worker {
        font-weight: 600;
        color: #334155;
    }
    .history-body {
        font-size: 15px;
        color: #1e293b;
        white-space: pre-wrap;
    }
    
    /* QR 스캔 결과 박스 */
    .qr-result-box {
        background-color: #ecfdf5;
        border: 1.5px solid #10b981;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.1);
    }
    
    /* 거래처 카드 컨테이너 */
    .client-container {
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 16px !important;
        align-items: stretch !important;
        justify-content: center !important;
        margin-top: 10px !important;
    }
    
    /* 거래처 카드 스타일 (HTML A 태그 대응 - 1줄에 1개, 가로 가득 채우기, 글씨 크고 가운데 정렬) */
    .client-card {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
        border: 2px solid #cbd5e1 !important;
        border-radius: 16px !important;
        padding: 24px 20px !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        color: #1e3a8a !important;
        text-align: center !important;
        text-decoration: none !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        width: 100% !important;
        box-sizing: border-box !important;
        cursor: pointer !important;
    }
    .client-card:hover {
        border-color: #3b82f6 !important;
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%) !important;
        color: #2563eb !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.15), 0 4px 6px -2px rgba(59, 130, 246, 0.1) !important;
    }
    .client-card:active {
        transform: translateY(1px) !important;
    }
    
    /* Streamlit element container overrides to force full width */
    div.element-container:has(.client-container),
    div.element-container:has(.client-card) {
        width: 100% !important;
        display: block !important;
    }
    div.stMarkdown:has(.client-container),
    div.stMarkdown:has(.client-card) {
        width: 100% !important;
        display: block !important;
    }
    div[data-testid="stMarkdownContainer"]:has(.client-container),
    div[data-testid="stMarkdownContainer"]:has(.client-card) {
        width: 100% !important;
        display: block !important;
    }
    div[data-testid="stMarkdownContainer"]:has(.client-container) > p,
    div[data-testid="stMarkdownContainer"]:has(.client-card) > p {
        width: 100% !important;
        display: block !important;
        margin: 0 !important;
    }
    
    /* Mobile optimization */
    @media (max-width: 640px) {
        .client-card {
            font-size: 18px !important;
            padding: 18px 12px !important;
            border-radius: 12px !important;
        }
    }

    /* Expander styling to match section-title */
    div[data-testid="stExpander"] {
        border: none !important;
        background-color: transparent !important;
        box-shadow: none !important;
        margin-bottom: 15px !important;
    }
    div[data-testid="stExpander"] details {
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        background-color: white !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        overflow: hidden !important;
    }
    div[data-testid="stExpander"] summary {
        background-color: #f8fafc !important;
        padding: 12px 16px !important;
        border-left: 4px solid #3b82f6 !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stExpander"] summary:hover {
        background-color: #eff6ff !important;
        color: #2563eb !important;
    }
    div[data-testid="stExpander"] summary span {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #1e3a8a !important;
    }
    div[data-testid="stExpander"] summary svg {
        fill: #1e3a8a !important;
    }

    /* Minimize default Streamlit padding at the top */
    .block-container,
    div[data-testid="stMainBlockContainer"],
    div[data-testid="stAppViewContainer"] {
        padding-top: 10px !important;
        padding-bottom: 10px !important;
        margin-top: 0px !important;
    }

    /* Force horizontal layout for the top buttons block (prevents collapsing to vertical) */
    [data-testid="stHorizontalBlock"]:has(.top-row-marker) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        gap: 12px !important;
        justify-content: flex-start !important;
    }
    [data-testid="stHorizontalBlock"]:has(.top-row-marker) > div {
        min-width: fit-content !important;
        width: auto !important;
        flex: 0 0 auto !important;
    }

    /* Force horizontal layout for the search row (prevents collapsing to vertical) */
    [data-testid="column"] [data-testid="stHorizontalBlock"]:has(.search-row-marker) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        gap: 8px !important;
        align-items: center !important;
    }
    [data-testid="column"] [data-testid="stHorizontalBlock"]:has(.search-row-marker) > div:nth-of-type(1) {
        width: 75% !important;
        min-width: 75% !important;
        flex: 0 0 75% !important;
    }
    [data-testid="column"] [data-testid="stHorizontalBlock"]:has(.search-row-marker) > div:nth-of-type(2) {
        width: 22% !important;
        min-width: 22% !important;
        flex: 0 0 22% !important;
    }

    /* Hide extra spacing of marker containers */
    .element-container:has(.top-row-marker),
    .element-container:has(.search-row-marker) {
        position: absolute !important;
        width: 0px !important;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
        border: none !important;
    }

    /* 서브메뉴 컨테이너 및 아이템 스타일 */
    .submenu-container {
        display: flex !important;
        flex-direction: row !important;
        gap: 12px !important;
        width: 100% !important;
        margin-bottom: 20px !important;
        margin-top: 10px !important;
    }
    .submenu-item {
        flex: 1 !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        background-color: white !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        color: #1e293b !important;
        text-align: center !important;
        text-decoration: none !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
    }
    .submenu-item:hover {
        border-color: #3b82f6 !important;
        background-color: #eff6ff !important;
        color: #2563eb !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.15) !important;
    }
    .submenu-item.active {
        border-color: #2563eb !important;
        background-color: #eff6ff !important;
        color: #2563eb !important;
        font-weight: 700 !important;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.06) !important;
    }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# Streamlit Cloud의 iframe 주소창을 부모 브라우저 주소창과 강제 동기화하는 JS 인젝션
import streamlit.components.v1 as components
components.html(
    """
    <script>
    if (window.parent && window.parent.location) {
        const checkAndSync = () => {
            try {
                const currentQuery = window.location.search;
                const parentQuery = window.parent.location.search;
                if (currentQuery !== parentQuery) {
                    window.parent.history.replaceState(null, null, currentQuery);
                }
            } catch (e) {
                // 크로스 도메인 보안 제약 예방
                console.error(e);
            }
        };
        checkAndSync();
        window.addEventListener('popstate', checkAndSync);
        setInterval(checkAndSync, 400); // 0.4초 간격으로 강제 갱신
    }
    </script>
    """,
    height=0,
    width=0
)

# 쿼리 파라미터 동기화 함수 정의
def sync_query_params():
    # 1. 작업자 동기화
    if st.session_state.get("authenticated") and st.session_state.get("login_worker"):
        if st.query_params.get("worker") != st.session_state.login_worker:
            st.query_params["worker"] = st.session_state.login_worker
    else:
        if "worker" in st.query_params:
            del st.query_params["worker"]
            
    # 2. 거래처 동기화
    if st.session_state.get("selected_client"):
        if st.query_params.get("client") != st.session_state.selected_client:
            st.query_params["client"] = st.session_state.selected_client
    else:
        if "client" in st.query_params:
            del st.query_params["client"]
            
    # 3. 메뉴 동기화
    if st.session_state.get("new_eq_form_open") and st.session_state.get("mgmt_sub_menu"):
        if st.query_params.get("menu") != st.session_state.mgmt_sub_menu:
            st.query_params["menu"] = st.session_state.mgmt_sub_menu
    else:
        if "menu" in st.query_params:
            del st.query_params["menu"]

    # 4. 설비 ID 동기화 (새로고침 대응)
    if st.session_state.get("selected_eq_id"):
        if st.query_params.get("eq_id") != st.session_state.selected_eq_id:
            st.query_params["eq_id"] = st.session_state.selected_eq_id
    else:
        if "eq_id" in st.query_params:
            del st.query_params["eq_id"]

    # 5. 검색어 동기화 (새로고침 대응)
    if st.session_state.get("search_performed") and st.session_state.get("search_query"):
        if st.query_params.get("q") != st.session_state.search_query:
            st.query_params["q"] = st.session_state.search_query
    else:
        if "q" in st.query_params:
            del st.query_params["q"]

# 3. 세션 상태 초기화
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "selected_client" not in st.session_state:
    st.session_state.selected_client = None
if "selected_eq_id" not in st.session_state:
    st.session_state.selected_eq_id = None
if "search_filter_id" not in st.session_state:
    st.session_state.search_filter_id = None
if "show_all" not in st.session_state:
    st.session_state.show_all = True
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "edit_history_id" not in st.session_state:
    st.session_state.edit_history_id = None
if "new_eq_form_open" not in st.session_state:
    st.session_state.new_eq_form_open = False
if "mgmt_sub_menu" not in st.session_state:
    st.session_state.mgmt_sub_menu = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "search_result_eq_id" not in st.session_state:
    st.session_state.search_result_eq_id = None
if "last_search_query" not in st.session_state:
    st.session_state.last_search_query = ""
if "search_performed" not in st.session_state:
    st.session_state.search_performed = False
if "edit_search_query" not in st.session_state:
    st.session_state.edit_search_query = ""
if "edit_search_performed" not in st.session_state:
    st.session_state.edit_search_performed = False
if "edit_selected_eq_id" not in st.session_state:
    st.session_state.edit_selected_eq_id = None
if "sync_logs" not in st.session_state:
    st.session_state.sync_logs = []
# URL 쿼리 파라미터와 st.session_state 간의 실시간 양방향 내비게이션 동기화 처리 (스마트폰 뒤로가기 완벽 연동)
def handle_navigation_sync():
    # 1. 로그인 상태 복구 및 연동
    url_worker = st.query_params.get("worker")
    if url_worker and not st.session_state.authenticated:
        st.session_state.authenticated = True
        st.session_state.login_worker = url_worker
        st.rerun()
    elif not url_worker and st.session_state.authenticated:
        st.session_state.authenticated = False
        st.session_state.login_worker = None
        st.rerun()
        
    # 2. 거래처 선택 상태 동기화 (뒤로가기 시 client 해제 감지)
    url_client = st.query_params.get("client")
    if url_client != st.session_state.selected_client:
        st.session_state.selected_client = url_client
        st.session_state.selected_eq_id = None
        st.session_state.search_filter_id = None
        st.session_state.show_all = True
        st.session_state.edit_mode = False
        st.session_state.search_result_eq_id = None
        st.session_state.search_query = ""
        st.session_state.last_search_query = ""
        st.session_state.search_performed = False
        st.session_state.edit_search_query = ""
        st.session_state.edit_search_performed = False
        st.session_state.edit_selected_eq_id = None
        st.rerun()
        
    # 3. 설비 ID 선택 상태 동기화 (뒤로가기 시 eq_id 해제 감지)
    url_eq_id = st.query_params.get("eq_id")
    if url_eq_id != st.session_state.selected_eq_id:
        st.session_state.selected_eq_id = url_eq_id
        st.session_state.search_result_eq_id = url_eq_id
        st.rerun()
        
    # 4. 메뉴 상태 동기화
    url_menu = st.query_params.get("menu")
    if url_menu != st.session_state.mgmt_sub_menu:
        st.session_state.mgmt_sub_menu = url_menu
        st.session_state.new_eq_form_open = bool(url_menu)
        st.rerun()
        
    # 5. 검색어 동기화
    url_q = st.query_params.get("q") or ""
    if url_q != st.session_state.search_query:
        st.session_state.search_query = url_q
        st.session_state.last_search_query = url_q
        st.session_state.search_performed = bool(url_q)
        st.rerun()

# 내비게이션 싱크 실행 및 파라미터 실시간 업데이트
handle_navigation_sync()
sync_query_params()

# --- 콜백 함수 정의 ---
# (QR 기능이 제거되어 이전 함수는 삭제됨)

# --- 비밀번호 로그인 체크 로직 ---
if "login_worker" not in st.session_state:
    st.session_state.login_worker = None

if not st.session_state.authenticated:
    # 3열 레이아웃을 사용하여 화면 중앙에 로그인 카드 배치
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        st.markdown('<div style="height: 50px;"></div>', unsafe_allow_html=True) # 상단 여백
        st.markdown('<h2 style="text-align: center; color: #1e3a8a; font-weight: 800; margin-bottom: 15px; font-size: 22px;">🔒 카스테크 현장 점검 로그인</h2>', unsafe_allow_html=True)
        
        with st.container(border=True):
            # 데이터베이스에 있는 기존 작업자 목록 조회
            db_workers = database.get_workers()
            worker_options = ["선택하세요"] + db_workers + ["새 작업자 직접 등록..."]
            selected_worker = st.selectbox("작업자 선택", options=worker_options)
            
            final_worker = ""
            if selected_worker == "새 작업자 직접 등록...":
                final_worker = st.text_input("새 작업자 이름 입력", placeholder="이름을 입력하세요").strip()
            else:
                final_worker = selected_worker
                
            pw_input = st.text_input("현장 비밀번호", type="password", placeholder="비밀번호 입력")
            
            if st.button("🔓 로그인"):
                if final_worker == "선택하세요" or not final_worker:
                    st.error("작업자를 선택하거나 새 작업자 이름을 입력해 주세요.")
                elif not pw_input:
                    st.error("비밀번호를 입력해 주세요.")
                else:
                    # 기존 작업자인 경우 DB 비밀번호와 매칭
                    if selected_worker != "새 작업자 직접 등록..." and final_worker in db_workers:
                        db_pw = database.get_worker_password(final_worker)
                        if pw_input != db_pw:
                            st.error("비밀번호가 일치하지 않습니다. 다시 확인해 주세요.")
                        else:
                            st.session_state.authenticated = True
                            st.session_state.login_worker = final_worker
                            st.session_state.selected_client = None
                            st.success(f"{final_worker}님 로그인 성공!")
                            sync_query_params()
                            st.rerun()
                    else:
                        # 새 작업자 등록 시도
                        if final_worker in db_workers:
                            st.error("이미 존재하는 작업자 이름입니다. 목록에서 선택 후 로그인해 주세요.")
                        else:
                            ok, msg = database.register_new_worker(final_worker, pw_input)
                            if ok:
                                st.session_state.authenticated = True
                                st.session_state.login_worker = final_worker
                                st.session_state.selected_client = None
                                st.success(f"새 작업자 '{final_worker}' 등록 및 로그인 성공!")
                                sync_query_params()
                                st.rerun()
                            else:
                                st.error(f"작업자 등록 실패: {msg}")
                                
    st.stop() # 로그인이 완료되지 않았으므로 아래의 모든 코드 실행 중단 및 화면 잠금

# (QR 코드 디코딩 함수 삭제됨)

# 5. 메인 레이아웃 렌더링
if st.session_state.selected_client is None:
    # ==========================================
    # [첫화면]: 거래처 선택 및 관리만 노출
    # ==========================================
    
    st.markdown("""
    <div class="main-header">
        <h1>📐 CAS-TECH 현장 점검 관리 웹</h1>
        <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">작업자: st.session_state.login_worker</p>
    </div>
    """.replace("st.session_state.login_worker", f"👤 <b>{st.session_state.login_worker}</b>"), unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">🏢 거래처 선택</div>', unsafe_allow_html=True)
    clients = database.get_clients()
    
    if not clients:
        st.info("데이터베이스에 등록된 거래처가 없습니다. 먼저 엑셀 마스터를 임포트하거나 아래에서 새 거래처를 등록해 주세요.")
    else:
        # 거래처 목록을 2열 그리드로 배치하여 모바일 네이티브 연동 보장
        if clients:
            cols = st.columns(2)
            for idx, client in enumerate(clients):
                col_idx = idx % 2
                with cols[col_idx]:
                    if st.button(f"🏢 {client}", key=f"client_btn_{idx}", use_container_width=True):
                        try:
                            database.sync_pull_from_github()
                        except Exception:
                            pass
                        st.session_state.selected_client = client
                        st.session_state.selected_eq_id = None
                        st.session_state.search_filter_id = None
                        st.session_state.show_all = True
                        st.session_state.edit_mode = False
                        st.session_state.search_result_eq_id = None
                        st.session_state.search_query = ""
                        st.session_state.last_search_query = ""
                        st.session_state.search_performed = False
                        st.session_state.edit_search_query = ""
                        st.session_state.edit_search_performed = False
                        st.session_state.edit_selected_eq_id = None
                        sync_query_params()
                        st.rerun()
                    
    # 거래처 추가 및 수정 메뉴
    st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">⚙️ 거래처 관리 (추가 및 이름 변경)</div>', unsafe_allow_html=True)
    
    with st.expander("🔧 거래처 추가 / 이름 수정 패널 열기", expanded=False):
        tab1, tab2 = st.tabs(["➕ 새 거래처 등록", "✏️ 기존 거래처명 변경"])
        
        with tab1:
            with st.form("add_client_form", clear_on_submit=True):
                new_client = st.text_input("등록할 새 거래처명 입력", placeholder="예: 삼성전자 기흥공장")
                submit_add = st.form_submit_button("💾 거래처 등록")
                if submit_add:
                    if not new_client:
                        st.error("거래처명을 입력해 주세요.")
                    else:
                        ok, msg = database.add_client(new_client)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                            
        with tab2:
            with st.form("rename_client_form", clear_on_submit=True):
                if clients:
                    client_to_rename = st.selectbox("변경할 거래처 선택", options=clients)
                    new_name = st.text_input("새로운 거래처명 입력", placeholder="예: KCC안성1공장")
                    submit_rename = st.form_submit_button("💾 거래처명 변경")
                    if submit_rename:
                        if not new_name:
                            st.error("변경할 새로운 거래처명을 입력해 주세요.")
                        else:
                            ok, msg = database.rename_client(client_to_rename, new_name)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                else:
                    st.info("등록된 거래처가 없습니다.")
                    
    # ----------------------------------------------------
    # 비밀번호 변경 익스팬더 (화면 제일 하단으로 배치)
    # ----------------------------------------------------
    st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)
    with st.expander("👤 내 비밀번호 변경", expanded=False):
        st.markdown(f"현재 로그인된 작업자: **{st.session_state.login_worker}**")
        curr_pw = st.text_input("현재 비밀번호", type="password", key="chg_curr_pw")
        new_pw = st.text_input("새 비밀번호", type="password", key="chg_new_pw")
        confirm_pw = st.text_input("새 비밀번호 확인", type="password", key="chg_confirm_pw")
        if st.button("💾 비밀번호 변경 실행", key="chg_pw_btn"):
            if not curr_pw or not new_pw or not confirm_pw:
                st.error("모든 항목을 입력해 주세요.")
            elif new_pw != confirm_pw:
                st.error("새 비밀번호와 확인이 일치하지 않습니다.")
            else:
                db_pw = database.get_worker_password(st.session_state.login_worker)
                if curr_pw != db_pw:
                    st.error("현재 비밀번호가 일치하지 않습니다.")
                else:
                    ok, msg = database.change_worker_password(st.session_state.login_worker, new_pw)
                    if ok:
                        st.success("비밀번호가 성공적으로 변경되었습니다!")
                    else:
                        st.error(msg)

else:
    # ==========================================
    # [다음화면]: 특정 거래처 진입 시 (검색, 목록 등)
    # ==========================================
    pass

# 9. 계기 관리 (거래처 진입 시 활성화)
    col_top_btns = st.columns([1, 1.2, 5])
    with col_top_btns[0]:
        st.markdown('<div class="top-row-marker" style="position: absolute; width: 0; height: 0; opacity: 0; pointer-events: none;"></div>', unsafe_allow_html=True)
        if st.button("⬅️ 돌아가기", key="back_to_home_btn"):
            try:
                database.sync_pull_from_github()
            except Exception:
                pass
            if st.session_state.new_eq_form_open:
                st.session_state.new_eq_form_open = False
                st.session_state.mgmt_sub_menu = None
            else:
                st.session_state.selected_client = None
                st.session_state.selected_eq_id = None
                st.session_state.search_filter_id = None
                st.session_state.show_all = True
                st.session_state.edit_mode = False
                st.session_state.search_result_eq_id = None
                st.session_state.search_query = ""
                st.session_state.last_search_query = ""
                st.session_state.search_performed = False
            sync_query_params()
            st.rerun()
            
    with col_top_btns[1]:
        if not st.session_state.new_eq_form_open:
            if st.button("🔧 계기등록 및 관리", key="new_eq_toggle_btn"):
                st.session_state.new_eq_form_open = True
                sync_query_params()
                st.rerun()
            
    st.write("") # 작은 공백 여백
    
    # 9-2. 새 계기 등록 및 목록 레이아웃
    if not st.session_state.new_eq_form_open:
        col_list = st.container()
        col_form = st.container()
    else:
        col_list, col_form = None, None
    
    if st.session_state.new_eq_form_open:
        st.markdown('<div class="section-title">🔧 계기등록 및 관리</div>', unsafe_allow_html=True)
        
        # Render the custom sub-menu bar using native buttons
        col_menu1, col_menu2 = st.columns(2)
        with col_menu1:
            btn_label1 = "🎯 ➕ 계기등록 및 수정" if st.session_state.mgmt_sub_menu == "new_eq" else "➕ 계기등록 및 수정"
            if st.button(btn_label1, key="btn_menu_new_eq", use_container_width=True):
                st.session_state.mgmt_sub_menu = "new_eq"
                st.session_state.new_eq_form_open = True
                sync_query_params()
                st.rerun()
        with col_menu2:
            btn_label2 = "🎯 📅 수리점검내역" if st.session_state.mgmt_sub_menu == "history" else "📅 수리점검내역"
            if st.button(btn_label2, key="btn_menu_history", use_container_width=True):
                st.session_state.mgmt_sub_menu = "history"
                st.session_state.new_eq_form_open = True
                sync_query_params()
                st.rerun()
        
        if st.session_state.mgmt_sub_menu == "new_eq":
            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
            
            mode = st.radio("작업 모드 선택", options=["➕ 신규 계기 등록", "✏️ 기존 계기 정보 수정"], horizontal=True, key="eq_mgmt_mode")
            st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
            
            eq_list = database.get_equipments(st.session_state.selected_client)
            
            if mode == "➕ 신규 계기 등록":
                with st.form("new_eq_form", clear_on_submit=True):
                    new_id = st.text_input("설비 ID (필수)", placeholder="예: WE-1308")
                    new_name = st.text_input("설비명 (필수)", placeholder="예: 입식 지게차 2000kg")
                    new_loc = st.text_input("설치위치")
                    new_ip = st.text_input("계측기 IP")
                    new_ind = st.text_input("인디게이터")
                    new_lc = st.text_input("로드셀")
                    new_fmt = st.text_input("형식")
                    new_date = st.text_input("설치년월")
                    
                    # 사진 첨부
                    photo1 = st.file_uploader("설비 사진 1", type=["png", "jpg", "jpeg"])
                    photo2 = st.file_uploader("설비 사진 2", type=["png", "jpg", "jpeg"])
                    
                    submit_new = st.form_submit_button("💾 등록하기")
                    if submit_new:
                        if not new_id or not new_name:
                            st.error("설비 ID와 설비명은 필수 입력 항목입니다.")
                        else:
                            # 사진 파일 로컬 저장
                            p1_path = ""
                            p2_path = ""
                            if photo1:
                                p1_path = os.path.join(PHOTOS_DIR, f"{new_id}_1.jpg")
                                database.save_and_compress_image(photo1, p1_path)
                                database.upload_photo_to_github(p1_path)
                            if photo2:
                                p2_path = os.path.join(PHOTOS_DIR, f"{new_id}_2.jpg")
                                database.save_and_compress_image(photo2, p2_path)
                                database.upload_photo_to_github(p2_path)
                                    
                            eq_data = {
                                "거래처명": st.session_state.selected_client,
                                "설비ID": new_id.strip(),
                                "설비명": new_name.strip(),
                                "설치위치": new_loc.strip(),
                                "계측기_IP": new_ip.strip(),
                                "인디게이터": new_ind.strip(),
                                "로드셀": new_lc.strip(),
                                "형식": new_fmt.strip(),
                                "설치년월": new_date.strip(),
                                "설비사진1": p1_path,
                                "설비사진2": p2_path
                            }
                            
                            ok, msg = database.add_equipment(eq_data)
                            if ok:
                                st.success(msg)
                                st.session_state.new_eq_form_open = False
                                st.session_state.mgmt_sub_menu = None
                                sync_query_params()
                                st.rerun()
                            else:
                                st.error(msg)
            else:
                # 기존 계기 정보 수정 모드
                if not eq_list:
                    st.info("수정할 수 있는 계기가 없습니다. 신규 등록을 먼저 해주세요.")
                else:
                    # 1. 수정 전용 검색 영역
                    st.write("**✏️ 수정할 계기 검색 및 선택**")
                    col_edit_search_input, col_edit_search_btn = st.columns([3, 1])
                    with col_edit_search_input:
                        edit_search_input = st.text_input(
                            "수정할 계기 ID 또는 계기명을 입력하세요",
                            value=st.session_state.get("edit_search_query", ""),
                            placeholder="문자나 숫자를 입력하세요 (빈칸 검색 시 전체 표시)",
                            label_visibility="collapsed",
                            key="edit_eq_search_input"
                        )
                        edit_search_query_stripped = edit_search_input.strip()

                    with col_edit_search_btn:
                        confirm_edit_search = st.button("🔍 검색", key="confirm_edit_search_btn", use_container_width=True)

                    if edit_search_query_stripped != st.session_state.get("edit_search_query", ""):
                        st.session_state.edit_search_query = edit_search_query_stripped

                    if confirm_edit_search:
                        st.session_state.edit_search_performed = True
                        st.session_state.edit_selected_eq_id = None
                        st.rerun()

                    # 2. 검색 이력에 따라 매칭되는 데이터를 리스트 형태로 나열
                    if st.session_state.get("edit_search_performed", False):
                        if len(st.session_state.edit_search_query) == 0:
                            matching_edit_eqs = eq_list
                        else:
                            matching_edit_eqs = [
                                eq for eq in eq_list
                                if st.session_state.edit_search_query.lower() in eq["설비ID"].lower() or st.session_state.edit_search_query.lower() in eq["설비명"].lower()
                            ]

                        if matching_edit_eqs:
                            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
                            st.write(f"📋 **수정 대상 검색 결과 ({len(matching_edit_eqs)}건)**")
                            st.write("아래에서 수정할 계기를 터치(클릭)하면 정보 수정 폼이 활성화됩니다:")
                            
                            for eq in matching_edit_eqs:
                                is_selected = (eq["설비ID"] == st.session_state.get("edit_selected_eq_id"))
                                btn_prefix = "🎯 " if is_selected else "⚙️ "
                                btn_label = f"{btn_prefix}[{eq['설비ID']}] {eq['설비명']} ({eq['설치위치'] or '위치 미지정'})"
                                
                                if st.button(btn_label, key=f"btn_edit_list_select_{eq['설비ID']}", use_container_width=True):
                                    st.session_state.edit_selected_eq_id = eq["설비ID"]
                                    st.rerun()
                        else:
                            st.warning("⚠️ 검색어와 일치하는 계기가 없습니다. 다시 검색해 주세요.")

                    # 3. 계기가 최종 선택되었을 때만 수정 폼 활성화
                    if st.session_state.get("edit_selected_eq_id"):
                        eq_data = database.get_equipment_by_id(st.session_state.edit_selected_eq_id)
                        
                        if eq_data:
                            st.markdown("---")
                            st.write(f"⚙️ **[{eq_data['설비ID']}] {eq_data['설비명']} 정보 수정**")
                            with st.form("edit_eq_form", clear_on_submit=False):
                                edit_id = st.text_input("설비 ID (필수)", value=eq_data["설비ID"])
                                edit_name = st.text_input("설비명 (필수)", value=eq_data["설비명"])
                                edit_loc = st.text_input("설치위치", value=eq_data["설치위치"] or "")
                                edit_ip = st.text_input("계측기 IP", value=eq_data["계측기_IP"] or "")
                                edit_ind = st.text_input("인디게이터", value=eq_data["인디게이터"] or "")
                                edit_lc = st.text_input("로드셀", value=eq_data["로드셀"] or "")
                                edit_fmt = st.text_input("형식", value=eq_data["형식"] or "")
                                edit_date = st.text_input("설치년월", value=eq_data["설치년월"] or "")
                                
                                # 썸네일 크기로 보여주고 터치시 확대 지원하기 위해 컬럼 비율 조절 (use_container_width=True가 라이트박스 원본 확대를 지원함)
                                col_pic1, col_pic2, col_pic_space = st.columns([1.2, 1.2, 2.6])
                                p1_path = eq_data["설비사진1"]
                                p2_path = eq_data["설비사진2"]
                                if p1_path and isinstance(p1_path, str):
                                    p1_path = p1_path.replace("\\", "/")
                                if p2_path and isinstance(p2_path, str):
                                    p2_path = p2_path.replace("\\", "/")
                                    
                                with col_pic1:
                                    if p1_path:
                                        database.download_photo_from_github(p1_path)
                                    if p1_path and os.path.exists(p1_path):
                                        st.image(p1_path, caption="설비사진 1 (터치시 확대)", use_container_width=True)
                                    else:
                                        st.caption("등록된 사진 1 없음")
                                with col_pic2:
                                    if p2_path:
                                        database.download_photo_from_github(p2_path)
                                    if p2_path and os.path.exists(p2_path):
                                        st.image(p2_path, caption="설비사진 2 (터치시 확대)", use_container_width=True)
                                    else:
                                        st.caption("등록된 사진 2 없음")
                                        
                                edit_photo1 = st.file_uploader("새 설비 사진 1 업로드 (기존 사진을 변경하려면 업로드)", type=["png", "jpg", "jpeg"])
                                edit_photo2 = st.file_uploader("새 설비 사진 2 업로드 (기존 사진을 변경하려면 업로드)", type=["png", "jpg", "jpeg"])
                                
                                submit_edit = st.form_submit_button("💾 수정 완료")
                                if submit_edit:
                                    if not edit_id or not edit_name:
                                        st.error("설비 ID와 설비명은 필수 입력 항목입니다.")
                                    else:
                                        # 사진 파일 처리 (업로드 하지 않았으면 기존 경로 유지)
                                        p1_path = eq_data["설비사진1"] or ""
                                        p2_path = eq_data["설비사진2"] or ""
                                        if edit_photo1:
                                            p1_path = os.path.join(PHOTOS_DIR, f"{edit_id}_1.jpg")
                                            database.save_and_compress_image(edit_photo1, p1_path)
                                            database.upload_photo_to_github(p1_path)
                                        if edit_photo2:
                                            p2_path = os.path.join(PHOTOS_DIR, f"{edit_id}_2.jpg")
                                            database.save_and_compress_image(edit_photo2, p2_path)
                                            database.upload_photo_to_github(p2_path)
                                                
                                        updated_eq_data = {
                                            "거래처명": st.session_state.selected_client,
                                            "설비ID": edit_id.strip(),
                                            "설비명": edit_name.strip(),
                                            "설치위치": edit_loc.strip(),
                                            "계측기_IP": edit_ip.strip(),
                                            "인디게이터": edit_ind.strip(),
                                            "로드셀": edit_lc.strip(),
                                            "형식": edit_fmt.strip(),
                                            "설치년월": edit_date.strip(),
                                            "설비사진1": p1_path,
                                            "설비사진2": p2_path
                                        }
                                        
                                        ok, msg = database.update_equipment(eq_data["설비ID"], updated_eq_data)
                                        if ok:
                                            st.success(msg)
                                            st.session_state.new_eq_form_open = False
                                            st.session_state.mgmt_sub_menu = None
                                            st.session_state.selected_eq_id = edit_id.strip()
                                            st.session_state.search_result_eq_id = edit_id.strip()
                                            st.session_state.search_performed = True
                                            st.session_state.search_query = ""
                                            # 수정 성공 후 세션 상태 초기화
                                            st.session_state.edit_search_query = ""
                                            st.session_state.edit_search_performed = False
                                            st.session_state.edit_selected_eq_id = None
                                            sync_query_params()
                                            st.rerun()
                                        else:
                                            st.error(msg)
                            
        elif st.session_state.mgmt_sub_menu == "history":
            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                default_start = datetime.today().replace(day=1).date()
                start_date = st.date_input("조회 시작일", value=default_start, key="mgmt_start_date")
            with col_d2:
                default_end = datetime.today().date()
                end_date = st.date_input("조회 종료일", value=default_end, key="mgmt_end_date")
                
            # 계기별 필터 선택 박스 추가
            eq_list = database.get_equipments(st.session_state.selected_client)
            eq_options = ["전체 계기"] + [f"[{eq['설비ID']}] {eq['설비명']}" for eq in eq_list]
            selected_eq_filter = st.selectbox("조회할 계기 선택 (계기별)", options=eq_options)
            
            target_eq_id = None
            if selected_eq_filter != "전체 계기":
                target_eq_id = selected_eq_filter.split("]")[0].replace("[", "").strip()
                
            all_histories = database.get_histories()
            filtered_histories = []
            for h in all_histories:
                if h["거래처명"] != st.session_state.selected_client:
                    continue
                if target_eq_id and h["설비ID"] != target_eq_id:
                    continue
                dt_str = h["날짜_시간"]
                if not dt_str:
                    continue
                try:
                    h_date_str = dt_str[:10].strip()
                    h_date = datetime.strptime(h_date_str, "%Y-%m-%d").date()
                    if start_date <= h_date <= end_date:
                        filtered_histories.append(h)
                except Exception:
                    pass
                    
            if filtered_histories:
                st.write(f"📋 **조회된 수리/점검 내역 ({len(filtered_histories)}건)**")
                
                # PDF 보고서 생성 및 다운로드 버튼
                pdf_data = generate_pdf_report(
                    st.session_state.selected_client,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    selected_eq_filter,
                    filtered_histories
                )
                
                st.download_button(
                    label="📄 PDF 보고서 출력 및 다운로드",
                    data=pdf_data,
                    file_name=f"수리점검보고서_{st.session_state.selected_client}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    key="btn_download_pdf_report",
                    use_container_width=True
                )
                st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
                for item in filtered_histories:
                    eq_detail = database.get_equipment_by_id(item['설비ID'])
                    eq_name = eq_detail['설비명'] if eq_detail else "알 수 없는 설비"
                    
                    expander_title = f"⚙️ [{item['설비ID']}] {eq_name}  |  👤 {item['작업자명'] or '미지정'}  |  📅 {item['날짜_시간'] or '날짜 없음'}"
                    with st.expander(expander_title, expanded=False):
                        st.markdown(f"""
                        **[설비 ID]** {item['설비ID']}  
                        **[설비명]** {eq_name}  
                        **[작업자]** {item['작업자명'] or '-'}  
                        **[날짜]** {item['날짜_시간'] or '-'}  
                        **[증상]** {item['증상상태'] or '-'}  
                        **[조치 및 수리내용]** {item['조치_및_수리내용'] or '-'}
                        """)
                        
                        h_pic1 = item['사진1']
                        h_pic2 = item['사진2']
                        if h_pic1 and isinstance(h_pic1, str):
                            h_pic1 = h_pic1.replace("\\", "/")
                        if h_pic2 and isinstance(h_pic2, str):
                            h_pic2 = h_pic2.replace("\\", "/")
                            
                        if h_pic1:
                            database.download_photo_from_github(h_pic1)
                        if h_pic2:
                            database.download_photo_from_github(h_pic2)
                        if (h_pic1 and os.path.exists(h_pic1)) or (h_pic2 and os.path.exists(h_pic2)):
                            col_pic1, col_pic2 = st.columns(2)
                            if h_pic1 and os.path.exists(h_pic1):
                                with col_pic1:
                                    st.image(h_pic1, caption="조치 사진1", use_container_width=True)
                            if h_pic2 and os.path.exists(h_pic2):
                                with col_pic2:
                                    st.image(h_pic2, caption="조치 사진2", use_container_width=True)
            else:
                st.info("📅 해당 기간 내에 등록된 수리/점검 내역이 없습니다.")
        else:
            st.markdown("""
            <div style="background-color: #eff6ff; border: 1.5px solid #bfdbfe; border-radius: 12px; padding: 25px; text-align: center; margin-top: 10px;">
                <p style="margin: 0; font-size: 16px; font-weight: 700; color: #1e3a8a;">
                    💡 위의 메뉴에서 실행할 작업을 선택해 주세요.
                </p>
                <p style="margin: 8px 0 0 0; font-size: 14px; color: #3b82f6;">
                    계기를 등록하거나 수정하려면 <b>계기등록및수정</b>을, 거래처의 수리/점검내역을 조회하려면 <b>수리점검내역</b>을 터치하세요.
                </p>
            </div>
            """, unsafe_allow_html=True)
        st.stop()
    else:
        with col_list:
            st.write(f"**🔍 계기 검색 및 선택 ({st.session_state.selected_client})**")
            
            # 전체 계기 목록 가져오기
            eq_list = database.get_equipments(st.session_state.selected_client)
            
            # 1. 검색 입력창 및 검색 버튼 한 줄 배치 (폭을 줄여 검색창 3, 버튼 1 비율로 설정)
            col_search_input, col_search_btn = st.columns([3, 1])
            with col_search_input:
                st.markdown('<div class="search-row-marker" style="position: absolute; width: 0; height: 0; opacity: 0; pointer-events: none;"></div>', unsafe_allow_html=True)
                search_input = st.text_input(
                    "검색할 계기 ID 또는 계기명을 입력하세요",
                    value=st.session_state.search_query,
                    placeholder="문자나 숫자를 입력하세요 (빈칸 검색 시 전체 표시)",
                    label_visibility="collapsed",
                    key="eq_search_input"
                )
                search_query_stripped = search_input.strip()

            with col_search_btn:
                confirm_search = st.button("🔍 검색", key="confirm_search_btn", use_container_width=True)

            # 사용자가 검색 입력란을 수정하면 세션 상태 갱신
            if search_query_stripped != st.session_state.search_query:
                st.session_state.search_query = search_query_stripped
                st.session_state.last_search_query = search_query_stripped
            
            if confirm_search:
                try:
                    database.sync_pull_from_github()
                except Exception:
                    pass
                st.session_state.search_performed = True
                
                # 검색 버튼을 새로 누르면 기존의 상세 정보 선택 상태는 닫습니다
                st.session_state.selected_eq_id = None
                st.session_state.search_result_eq_id = None
                
                # 쿼리 파라미터 즉시 동기화 (새로고침/뒤로가기 초기화 방지)
                if len(search_query_stripped) == 0:
                    if "q" in st.query_params:
                        del st.query_params["q"]
                    if "eq_id" in st.query_params:
                        del st.query_params["eq_id"]
                else:
                    st.query_params["q"] = search_query_stripped
                    if "eq_id" in st.query_params:
                        del st.query_params["eq_id"]
                st.rerun()
                
            # 2. 검색 이력에 따라 매칭되는 데이터를 리스트(터치식 버튼 목록) 형태로 표시 (selectbox 드롭다운 제거 및 리스트 형태 롤백)
            if st.session_state.get("search_performed", False):
                # 검색어가 비어 있으면 전체, 있으면 필터링하여 나열
                if len(st.session_state.search_query) == 0:
                    matching_eqs = eq_list
                else:
                    matching_eqs = [
                        eq for eq in eq_list
                        if st.session_state.search_query.lower() in eq["설비ID"].lower() or st.session_state.search_query.lower() in eq["설비명"].lower()
                    ]
                
                if matching_eqs:
                    st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
                    st.write(f"📋 **검색 결과 ({len(matching_eqs)}건)**")
                    st.write("아래에서 계기를 터치(클릭)하면 상세 정보와 등록 폼이 활성화됩니다:")
                    
                    for eq in matching_eqs:
                        # 현재 선택된 계기 표시 (🎯 아이콘 및 강조 스타일)
                        is_selected = (eq["설비ID"] == st.session_state.selected_eq_id)
                        btn_prefix = "🎯 " if is_selected else "⚙️ "
                        btn_label = f"{btn_prefix}[{eq['설비ID']}] {eq['설비명']} ({eq['설치위치'] or '위치 미지정'})"
                        
                        # 터치식 리스트 버튼 렌더링
                        if st.button(btn_label, key=f"btn_list_select_{eq['설비ID']}", use_container_width=True):
                            st.session_state.selected_eq_id = eq["설비ID"]
                            st.session_state.search_result_eq_id = eq["설비ID"]
                            # 쿼리 파라미터 즉시 업데이트하여 handle_navigation_sync로 인한 덮어쓰기 방지
                            st.query_params["eq_id"] = eq["설비ID"]
                            st.rerun()
                else:
                    if len(st.session_state.search_query) > 0:
                        st.warning("⚠️ 검색어와 일치하는 계기가 없습니다. 다시 검색해 주세요.")
        
    # 9-3. 점검 폼 및 이력 영역 (우측 컬럼)
    with col_form:
        # 검색 결과가 존재하며 선택된 계기가 있을 때만 노출
        if st.session_state.search_result_eq_id and st.session_state.selected_eq_id:
            eq_detail = database.get_equipment_by_id(st.session_state.selected_eq_id)
            
            if eq_detail:
                with st.container(border=False):
                    st.markdown(f'<div class="section-title">🔍 계기 상세 정보</div>', unsafe_allow_html=True)
                    st.write(f"**계기 ID:** {eq_detail['설비ID']}")
                    st.write(f"**계기명:** {eq_detail['설비명']}")
                    st.write(f"**설치위치:** {eq_detail['설치위치'] or '-'}")
                    st.write(f"**계측기 IP:** {eq_detail['계측기_IP'] or '-'}")
                    st.write(f"**인디게이터:** {eq_detail['인디게이터'] or '-'}")
                    st.write(f"**로드셀:** {eq_detail['로드셀'] or '-'}")
                    
                    # 사진이 등록되어 있을 시 노출
                    p1_path = eq_detail['설비사진1']
                    p2_path = eq_detail['설비사진2']
                    if p1_path and isinstance(p1_path, str):
                        p1_path = p1_path.replace("\\", "/")
                    if p2_path and isinstance(p2_path, str):
                        p2_path = p2_path.replace("\\", "/")
                        
                    if p1_path:
                        database.download_photo_from_github(p1_path)
                    if p2_path:
                        database.download_photo_from_github(p2_path)
                        
                    # 사진 노출 크기를 썸네일 크기로 대폭 줄이고 가로로 나란히 배치 (클릭 시 확대 가능)
                    if (p1_path and os.path.exists(p1_path)) or (p2_path and os.path.exists(p2_path)):
                        st.write("**설비 사진 (터치하면 확대됩니다):**")
                        # 썸네일 크기로 보여주고 터치시 확대 지원하기 위해 컬럼 비율 조절 (use_container_width=True가 라이트박스 원본 확대를 지원함)
                        col_pic1, col_pic2, col_pic_space = st.columns([1.2, 1.2, 2.6])
                        with col_pic1:
                            if p1_path and os.path.exists(p1_path):
                                st.image(p1_path, caption="설비사진 1", use_container_width=True)
                        with col_pic2:
                            if p2_path and os.path.exists(p2_path):
                                st.image(p2_path, caption="설비사진 2", use_container_width=True)
                
                # 점검/수리 등록 폼
                form_title = "➕ 점검 기록 등록"
                submit_label = "💾 점검 완료 등록"
                pre_date = datetime.today().date()
                pre_worker = st.session_state.get("login_worker", "선택하세요")
                
                with st.expander(form_title, expanded=False):
                    # 점검 이력 작성 폼 (Key를 고정하여 깔끔하게 처리)
                    form_key = "new_inspection_form"
                    with st.form(form_key):
                        # 1. 등록 날짜: 달력으로 날짜만 입력받기
                        input_date = st.date_input("점검 날짜", value=pre_date)
                        
                        # 2. 작업자명: selectbox 제공 (['선택하세요', 데이터베이스 내용]) + 직접 입력 지원
                        db_workers = database.get_workers()
                        worker_options = ["선택하세요"] + db_workers + ["직접 입력..."]
                        
                        if pre_worker not in worker_options:
                            worker_options.insert(1, pre_worker)
                            
                        worker_index = worker_options.index(pre_worker) if pre_worker in worker_options else 0
                        selected_worker = st.selectbox("작업자명 선택", options=worker_options, index=worker_index)
                        
                        # '직접 입력...' 선택 시 텍스트 인풋 제공
                        custom_worker = ""
                        if selected_worker == "직접 입력...":
                            custom_worker = st.text_input("새 작업자 이름 입력", placeholder="작업자 성함")
                            
                        input_symptom = st.text_input("증상 및 상태", value="")
                        input_action = st.text_area("조치 및 수리내용", value="")
                        input_cost = st.number_input("수리 비용(원)", value=0, step=1000)
                        
                        # 사진 첨부 (수리 전후 등)
                        hist_photo1 = st.file_uploader("현장/조치 사진 1", type=["png", "jpg", "jpeg"], key="hp1")
                        hist_photo2 = st.file_uploader("현장/조치 사진 2", type=["png", "jpg", "jpeg"], key="hp2")
                        
                        submit_hist = st.form_submit_button(submit_label)
                                    
                        if submit_hist:
                            # 최종 작업자명 설정
                            final_worker = custom_worker.strip() if selected_worker == "직접 입력..." else selected_worker
                            
                            if final_worker == "선택하세요" or not final_worker:
                                st.error("작업자명을 올바르게 선택하거나 입력해 주세요.")
                            elif not input_symptom or not input_action:
                                st.error("증상 및 조치내용은 필수 입력 사항입니다.")
                            else:
                                hp1_path = ""
                                hp2_path = ""
                                
                                # 새 사진 등록
                                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                                if hist_photo1:
                                    hp1_path = os.path.join(PHOTOS_DIR, f"hist_{st.session_state.selected_eq_id}_{timestamp}_1.jpg")
                                    database.save_and_compress_image(hist_photo1, hp1_path)
                                    database.upload_photo_to_github(hp1_path)
                                if hist_photo2:
                                    hp2_path = os.path.join(PHOTOS_DIR, f"hist_{st.session_state.selected_eq_id}_{timestamp}_2.jpg")
                                    database.save_and_compress_image(hist_photo2, hp2_path)
                                    database.upload_photo_to_github(hp2_path)
                                        
                                hist_data = {
                                    "날짜_시간": input_date.strftime("%Y-%m-%d"),
                                    "작업자명": final_worker,
                                    "거래처명": st.session_state.selected_client,
                                    "설비ID": st.session_state.selected_eq_id,
                                    "증상상태": input_symptom.strip(),
                                    "조치_및_수리내용": input_action.strip(),
                                    "사진1": hp1_path,
                                    "사진2": hp2_path,
                                    "금액": float(input_cost)
                                }
                                
                                # Insert 작업 실행
                                ok, msg = database.add_history(hist_data)
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                
                # 계기 과거 이력 리스트 (터치 수정 포함)
                with st.container(border=False):
                    st.markdown('<div class="section-title">📋 과거 점검/수리 이력</div>', unsafe_allow_html=True)
                    
                    eq_histories = database.get_histories(st.session_state.selected_eq_id)
                    if eq_histories:
                        for item in eq_histories:
                            # 1. 과거 수리 내역을 expander로 만들고 금액 표시 제거
                            expander_title = f"👤 {item['작업자명'] or '미지정'}  |  📅 {item['날짜_시간'] or '날짜 없음'}  |  [증상] {item['증상상태'] or '-'}"
                            with st.expander(expander_title, expanded=False):
                                st.markdown(f"""
                                **[증상]** {item['증상상태'] or '-'}  
                                **[조치]** {item['조치_및_수리내용'] or '-'}
                                """)
                                
                                # 사진 첨부 확인 및 배치
                                h_pic1 = item['사진1']
                                h_pic2 = item['사진2']
                                if h_pic1 and isinstance(h_pic1, str):
                                    h_pic1 = h_pic1.replace("\\", "/")
                                if h_pic2 and isinstance(h_pic2, str):
                                    h_pic2 = h_pic2.replace("\\", "/")
                                    
                                if h_pic1:
                                    database.download_photo_from_github(h_pic1)
                                if h_pic2:
                                    database.download_photo_from_github(h_pic2)
                                if (h_pic1 and os.path.exists(h_pic1)) or (h_pic2 and os.path.exists(h_pic2)):
                                    col_pic1, col_pic2 = st.columns(2)
                                    if h_pic1 and os.path.exists(h_pic1):
                                        with col_pic1:
                                            st.image(h_pic1, caption="조치 사진1", use_container_width=True)
                                            if st.button("🔍 크게 보기", key=f"zoom_hist_p1_{item['id']}"):
                                                show_large_image(h_pic1)
                                    if h_pic2 and os.path.exists(h_pic2):
                                        with col_pic2:
                                            st.image(h_pic2, caption="조치 사진2", use_container_width=True)
                                            if st.button("🔍 크게 보기", key=f"zoom_hist_p2_{item['id']}"):
                                                show_large_image(h_pic2)
                                            
                                # 내역 하단에 수정 가능한 입력폼 바로 제공 (수정하기 버튼 삭제)
                                st.markdown("---")
                                st.markdown("✏️ **이 점검 이력 수정하기**")
                                with st.form(key=f"edit_form_{item['id']}"):
                                    try:
                                        parsed_date = datetime.strptime(item['날짜_시간'][:10], "%Y-%m-%d").date()
                                    except Exception:
                                        parsed_date = datetime.today().date()
                                    edit_date = st.date_input("점검 날짜", value=parsed_date, key=f"ed_date_{item['id']}")
                                    
                                    db_workers = database.get_workers()
                                    worker_options = ["선택하세요"] + db_workers + ["직접 입력..."]
                                    pre_worker = item['작업자명'] or "선택하세요"
                                    if pre_worker not in worker_options:
                                        worker_options.insert(1, pre_worker)
                                    worker_index = worker_options.index(pre_worker) if pre_worker in worker_options else 0
                                    
                                    edit_worker = st.selectbox("작업자명 선택", options=worker_options, index=worker_index, key=f"ed_worker_{item['id']}")
                                    
                                    custom_worker = ""
                                    if edit_worker == "직접 입력...":
                                        custom_worker = st.text_input("새 작업자 이름 입력", placeholder="작업자 성함", key=f"ed_custom_worker_{item['id']}")
                                        
                                    edit_symptom = st.text_input("증상 및 상태", value=item['증상상태'] or "", key=f"ed_symptom_{item['id']}")
                                    edit_action = st.text_area("조치 및 수리내용", value=item['조치_및_수리내용'] or "", key=f"ed_action_{item['id']}")
                                    
                                    # 금액 및 사진 파일 수정 필드 제공
                                    edit_cost = st.number_input("수리 비용(원)", value=int(item['금액']) if item['금액'] is not None else 0, step=1000, key=f"ed_cost_{item['id']}")
                                    edit_photo1 = st.file_uploader("현장/조치 사진 1 수정", type=["png", "jpg", "jpeg"], key=f"ed_photo1_{item['id']}")
                                    edit_photo2 = st.file_uploader("현장/조치 사진 2 수정", type=["png", "jpg", "jpeg"], key=f"ed_photo2_{item['id']}")
                                    
                                    submit_edit = st.form_submit_button("💾 수정 완료")
                                    if submit_edit:
                                        final_worker = custom_worker.strip() if edit_worker == "직접 입력..." else edit_worker
                                        if final_worker == "선택하세요" or not final_worker:
                                            st.error("작업자명을 올바르게 선택하거나 입력해 주세요.")
                                        elif not edit_symptom or not edit_action:
                                            st.error("증상 및 조치내용은 필수 입력 사항입니다.")
                                        else:
                                            hp1_path = item['사진1']
                                            hp2_path = item['사진2']
                                            
                                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                                            if edit_photo1:
                                                hp1_path = os.path.join(PHOTOS_DIR, f"hist_{st.session_state.selected_eq_id}_{timestamp}_1.jpg")
                                                database.save_and_compress_image(edit_photo1, hp1_path)
                                                database.upload_photo_to_github(hp1_path)
                                            if edit_photo2:
                                                hp2_path = os.path.join(PHOTOS_DIR, f"hist_{st.session_state.selected_eq_id}_{timestamp}_2.jpg")
                                                database.save_and_compress_image(edit_photo2, hp2_path)
                                                database.upload_photo_to_github(hp2_path)
                                                    
                                            updated_data = {
                                                "날짜_시간": edit_date.strftime("%Y-%m-%d"),
                                                "작업자명": final_worker,
                                                "거래처명": st.session_state.selected_client,
                                                "설비ID": st.session_state.selected_eq_id,
                                                "증상상태": edit_symptom.strip(),
                                                "조치_및_수리내용": edit_action.strip(),
                                                "사진1": hp1_path,
                                                "사진2": hp2_path,
                                                "금액": float(edit_cost)
                                            }
                                            
                                            ok, msg = database.update_history(item['id'], updated_data)
                                            if ok:
                                                st.success(msg)
                                                st.rerun()
                                            else:
                                                st.error(msg)
                    else:
                        st.info("이 계기에 등록된 과거 점검 이력이 없습니다.")
        else:
            st.info("💡 왼쪽 검색창에 계기 ID 또는 명칭의 일부를 입력하고 🔍 검색을 완료하시면 상세 정보와 점검 등록 양식이 나타납니다.")


