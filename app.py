import streamlit as st
import pandas as pd
import numpy as np
import cv2
from PIL import Image
import os
from datetime import datetime
import database

# 1. 페이지 초기 설정 및 DB 생성
st.set_page_config(
    page_title="카스테크(CAS-TECH) 현장 점검 관리",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 데이터베이스 파일이 없는 경우 마이그레이션 실행
if not os.path.exists(database.DB_FILE):
    database.init_db()

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
    
    /* 헤더 스타일 */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
        border: 1px solid #2563eb;
    }
    .main-header h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: white !important;
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
    
    /* 모든 버튼 스타일 통일 및 호버 효과 */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #cbd5e1;
        background-color: white;
        color: #1e293b;
        font-weight: 600;
        padding: 10px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stButton > button:hover {
        border-color: #3b82f6;
        background-color: #eff6ff;
        color: #2563eb;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.15);
    }
    .stButton > button:active {
        transform: translateY(1px);
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
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# 3. 세션 상태 초기화
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "selected_client" not in st.session_state:
    st.session_state.selected_client = None
if "selected_eq_id" not in st.session_state:
    st.session_state.selected_eq_id = None
if "qr_scanned_id" not in st.session_state:
    st.session_state.qr_scanned_id = None
if "show_camera" not in st.session_state:
    st.session_state.show_camera = False
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

# --- 비밀번호 로그인 체크 로직 ---
# 사장님 설정: 초기 비밀번호를 변경하시려면 아래의 "1234" 부분을 변경하고 저장해 주세요.
APP_PASSWORD = "1234"

if not st.session_state.authenticated:
    st.markdown('<div class="lux-card" style="max-width: 450px; margin: 80px auto; padding: 40px; border-radius: 16px; border: 2px solid #e2e8f0;">', unsafe_allow_html=True)
    st.markdown('<h2 style="text-align: center; color: #1e3a8a; font-weight: 800; margin-bottom: 25px; font-size: 22px;">🔒 카스테크 현장 점검 시스템 로그인</h2>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        pw_input = st.text_input("현장 비밀번호를 입력해 주세요", type="password", placeholder="비밀번호 입력")
        submit_login = st.form_submit_button("🔓 로그인")
        
        if submit_login:
            if pw_input == APP_PASSWORD:
                st.session_state.authenticated = True
                st.success("로그인되었습니다! 화면을 준비 중입니다...")
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다. 다시 확인해 주세요.")
                
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop() # 로그인이 완료되지 않았으므로 아래의 모든 코드 실행 중단 및 화면 잠금

# 4. QR 코드 디코딩 함수
def decode_qr(image_file):
    try:
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(img)
        if data:
            return data
        return None
    except Exception as e:
        st.error(f"QR 코드 분석 중 오류 발생: {e}")
        return None

# 5. 메인 레이아웃 타이틀
st.markdown("""
<div class="main-header">
    <h1>📐 CAS-TECH 현장 점검 관리 웹</h1>
</div>
""", unsafe_allow_html=True)

# 6. QR 스캔 영역 (최상단 배치)
col_qr_btn, col_qr_txt = st.columns([1, 2])
with col_qr_btn:
    if st.button("📷 QR 스캔 카메라 토글"):
        st.session_state.show_camera = not st.session_state.show_camera
        st.session_state.qr_scanned_id = None
        st.rerun()

with col_qr_txt:
    qr_manual = st.text_input("QR 코드 직접 입력 (가상 스캔)", placeholder="계기ID 입력 후 Enter (예: WE-1307)")
    if qr_manual:
        st.session_state.qr_scanned_id = qr_manual.strip()
        st.session_state.show_camera = False

if st.session_state.show_camera:
    img_file = st.camera_input("카메라로 QR 코드를 비추고 촬영해 주세요.")
    if img_file is not None:
        scanned_id = decode_qr(img_file)
        if scanned_id:
            st.session_state.qr_scanned_id = scanned_id
            st.session_state.show_camera = False
            st.success(f"QR 코드 인식 성공: {scanned_id}")
            st.rerun()
        else:
            st.warning("QR 코드를 인식하지 못했습니다. 초점을 맞춰 다시 시도해 주세요.")

# 7. QR 스캔 결과 표시 (스캔된 계기 정보 최상단 조회)
if st.session_state.qr_scanned_id:
    eq_info = database.get_equipment_by_id(st.session_state.qr_scanned_id)
    
    st.markdown('<div class="qr-result-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔍 QR 스캔 결과</div>', unsafe_allow_html=True)
    
    if eq_info:
        # 설비 정보 상세 테이블 표시
        st.write(f"**거래처명:** {eq_info['거래처명']} | **설비ID:** {eq_info['설비ID']} | **설비명:** {eq_info['설비명']}")
        
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.write(f"**설치위치:** {eq_info['설치위치'] or '-'}")
        col_s2.write(f"**계측기 IP:** {eq_info['계측기_IP'] or '-'}")
        col_s3.write(f"**인디게이터:** {eq_info['인디게이터'] or '-'}")
        col_s4.write(f"**로드셀:** {eq_info['로드셀'] or '-'}")
        
        # 사진 표시
        photo1_path = eq_info['설비사진1']
        photo2_path = eq_info['설비사진2']
        if photo1_path and os.path.exists(photo1_path):
            st.image(photo1_path, caption="설비사진 1", width=200)
            
        # 과거 이력 조회
        st.write("---")
        st.write("**📋 과거 점검/수리 이력**")
        histories = database.get_histories(eq_info['설비ID'])
        if histories:
            hist_df = pd.DataFrame(histories)
            hist_df = hist_df.rename(columns={
                "날짜_시간": "점검일시",
                "작업자명": "작업자",
                "증상상태": "증상",
                "조치_및_수리내용": "조치내용",
                "금액": "비용(원)"
            })
            st.dataframe(hist_df[["점검일시", "작업자", "증상", "조치내용", "비용(원)"]], use_container_width=True)
        else:
            st.info("과거 점검 이력이 존재하지 않습니다.")
            
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("➕ 이 계기 점검 및 수리 시작"):
                st.session_state.selected_client = eq_info['거래처명']
                st.session_state.selected_eq_id = eq_info['설비ID']
                st.session_state.qr_scanned_id = None
                st.rerun()
        with col_act2:
            if st.button("❌ 닫기"):
                st.session_state.qr_scanned_id = None
                st.rerun()
    else:
        st.error(f"데이터베이스에 설비ID가 '{st.session_state.qr_scanned_id}'인 계기가 등록되어 있지 않습니다.")
        if st.button("❌ 닫기"):
            st.session_state.qr_scanned_id = None
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)

# 8. 거래처 목록 (큰 블록/카드 그리드 형태)
st.markdown('<div class="section-title">🏢 거래처 선택</div>', unsafe_allow_html=True)
clients = database.get_clients()

if not clients:
    st.info("데이터베이스에 등록된 거래처가 없습니다. 먼저 엑셀 마스터를 임포트하거나 새 계기를 등록해 주세요.")
else:
    # 4열 그리드 레이아웃
    cols = st.columns(4)
    for idx, client in enumerate(clients):
        col = cols[idx % 4]
        with col:
            # 거래처가 선택되어 있는 경우 보더 하이라이트
            button_label = f"🏢 {client}"
            if st.session_state.selected_client == client:
                button_label = f"✅ {client}"
            
            # st.button을 사용하여 카드 클릭 동작 구현
            if st.button(button_label, key=f"client_btn_{idx}"):
                st.session_state.selected_client = client
                st.session_state.selected_eq_id = None # 거래처 변경 시 선택 계기 초기화
                st.session_state.search_filter_id = None
                st.session_state.show_all = True
                st.session_state.edit_mode = False
                st.rerun()

# 9. 계기 관리 (거래처 진입 시 활성화)
if st.session_state.selected_client:
    st.write("---")
    st.markdown(f'<div class="section-title">🛠️ {st.session_state.selected_client} 계기 관리</div>', unsafe_allow_html=True)
    
    # 9-1. 검색창 특수 필터 (요구사항 반영)
    st.markdown('<div class="lux-card">', unsafe_allow_html=True)
    st.write("**🔍 계기 실시간 검색 및 필터**")
    
    # 검색 입력창
    search_query = st.text_input("계기 ID 또는 계기명을 입력하세요. (1자 이상 입력 시 하단에 매칭 목록 노출)", key="search_input")
    
    matched_eqs = []
    selected_option = None
    
    if len(search_query) >= 1:
        # 입력창에 1자 이상 입력했을 때 검색 목록 조회
        matched_eqs = database.get_equipments(st.session_state.selected_client, search_query)
        if matched_eqs:
            # 매칭 데이터 드롭다운 노출
            selected_option = st.selectbox(
                "검색 결과 목록에서 대상을 선택하세요:",
                options=matched_eqs,
                format_func=lambda x: f"[{x['설비ID']}] {x['설비명']} (위치: {x['설치위치'] or '-'})"
            )
        else:
            st.warning("일치하는 계기가 없습니다.")
            
    # 검색 버튼
    if st.button("검색"):
        if len(search_query) >= 1 and selected_option:
            # 선택한 데이터만 노출
            st.session_state.search_filter_id = selected_option["설비ID"]
            st.session_state.show_all = False
        else:
            # 빈 상태이거나 검색 결과가 없을 시 전체 데이터 노출
            st.session_state.search_filter_id = None
            st.session_state.show_all = True
        st.session_state.edit_mode = False
            
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 9-2. 새 계기 등록 및 목록 레이아웃
    col_list, col_form = st.columns([2, 1])
    
    with col_list:
        st.markdown('<div class="lux-card">', unsafe_allow_html=True)
        st.write(f"**📋 계기 목록 ({st.session_state.selected_client})**")
        
        # 목록 필터링 적용
        if st.session_state.show_all or not st.session_state.search_filter_id:
            eq_list = database.get_equipments(st.session_state.selected_client)
        else:
            eq_list = [database.get_equipment_by_id(st.session_state.search_filter_id)]
            # 혹시 조회 안되면 전체 가져옴
            if not eq_list or eq_list[0] is None:
                eq_list = database.get_equipments(st.session_state.selected_client)
                
        # 계기 목록 테이블 렌더링
        if eq_list:
            eq_df = pd.DataFrame(eq_list)
            eq_df_display = eq_df.rename(columns={
                "설비ID": "계기 ID",
                "설비명": "계기명",
                "설치위치": "설치위치",
                "계측기_IP": "계측기 IP",
                "인디게이터": "인디게이터",
                "로드셀": "로드셀"
            })
            
            # st.dataframe을 통해 고급 테이블 렌더링
            st.dataframe(
                eq_df_display[["계기 ID", "계기명", "설치위치", "계측기 IP", "인디게이터", "로드셀"]], 
                use_container_width=True, 
                hide_index=True
            )
            
            # 빠른 점검 선택
            st.write("**👇 아래 드롭다운에서 계기를 선택하면 상세 사양 확인 및 점검/이력 작성이 가능합니다.**")
            selected_eq = st.selectbox(
                "점검할 계기 선택",
                options=eq_list,
                format_func=lambda x: f"[{x['설비ID']}] {x['설비명']}",
                key="select_eq_dropdown"
            )
            if selected_eq:
                st.session_state.selected_eq_id = selected_eq["설비ID"]
        else:
            st.info("조회된 계기가 없습니다.")
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 새 계기 등록 토글 버튼 및 입력 창
        if st.button("➕ 새 계기 등록 토글"):
            st.session_state.new_eq_form_open = not st.session_state.new_eq_form_open
            
        if st.session_state.new_eq_form_open:
            st.markdown('<div class="lux-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">➕ 신규 계기 등록</div>', unsafe_allow_html=True)
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
                            with open(p1_path, "wb") as f:
                                f.write(photo1.getbuffer())
                        if photo2:
                            p2_path = os.path.join(PHOTOS_DIR, f"{new_id}_2.jpg")
                            with open(p2_path, "wb") as f:
                                f.write(photo2.getbuffer())
                                
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
                            st.rerun()
                        else:
                            st.error(msg)
            st.markdown('</div>', unsafe_allow_html=True)
            
    # 9-3. 점검 폼 및 이력 영역 (우측 컬럼)
    with col_form:
        if st.session_state.selected_eq_id:
            eq_detail = database.get_equipment_by_id(st.session_state.selected_eq_id)
            
            if eq_detail:
                st.markdown('<div class="lux-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="section-title">🔍 계기 상세 정보</div>', unsafe_allow_html=True)
                st.write(f"**계기 ID:** {eq_detail['설비ID']}")
                st.write(f"**계기명:** {eq_detail['설비명']}")
                st.write(f"**설치위치:** {eq_detail['설치위치'] or '-'}")
                st.write(f"**계측기 IP:** {eq_detail['계측기_IP'] or '-'}")
                st.write(f"**인디게이터:** {eq_detail['인디게이터'] or '-'}")
                st.write(f"**로드셀:** {eq_detail['로드셀'] or '-'}")
                
                # 사진이 등록되어 있을 시 노출
                if eq_detail['설비사진1'] and os.path.exists(eq_detail['설비사진1']):
                    st.image(eq_detail['설비사진1'], caption="설비사진 1", use_container_width=True)
                if eq_detail['설비사진2'] and os.path.exists(eq_detail['설비사진2']):
                    st.image(eq_detail['설비사진2'], caption="설비사진 2", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 점검/수리 등록 및 수정 폼
                st.markdown('<div class="lux-card">', unsafe_allow_html=True)
                
                form_title = "➕ 점검 기록 등록"
                submit_label = "💾 점검 완료 등록"
                
                # 수정 모드 데이터 세팅
                pre_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pre_worker = "선택하세요"
                pre_symptom = ""
                pre_action = ""
                pre_cost = 0.0
                
                if st.session_state.edit_mode and st.session_state.edit_history_id:
                    history_data = database.get_history_by_id(st.session_state.edit_history_id)
                    if history_data:
                        form_title = "✏️ 점검 기록 수정"
                        submit_label = "💾 수정 완료"
                        pre_date = history_data["날짜_시간"]
                        pre_worker = history_data["작업자명"] or "선택하세요"
                        pre_symptom = history_data["증상상태"] or ""
                        pre_action = history_data["조치_및_수리내용"] or ""
                        pre_cost = float(history_data["금액"]) if history_data["금액"] is not None else 0.0
                
                st.markdown(f'<div class="section-title">{form_title}</div>', unsafe_allow_html=True)
                
                # 점검 이력 작성 폼 (Key를 상태값에 따라 구분해 리렌더링 유도)
                form_key = f"inspection_form_{st.session_state.edit_mode}_{st.session_state.edit_history_id}"
                with st.form(form_key):
                    # 1. 등록 시간: 현재 DateTime 기본 노출 및 수정 가능 (요구사항 반영)
                    input_date = st.text_input("점검 일시 (YYYY-MM-DD HH:MM:SS)", value=pre_date)
                    
                    # 2. 작업자명: selectbox 제공 (['선택하세요', 데이터베이스 내용]) + 직접 입력 지원
                    db_workers = database.get_workers()
                    worker_options = ["선택하세요"] + db_workers + ["직접 입력..."]
                    
                    # 만약 기존 데이터의 작업자가 현재 옵션에 없으면 삽입
                    if pre_worker not in worker_options:
                        worker_options.insert(1, pre_worker)
                        
                    worker_index = worker_options.index(pre_worker) if pre_worker in worker_options else 0
                    selected_worker = st.selectbox("작업자명 선택", options=worker_options, index=worker_index)
                    
                    # '직접 입력...' 선택 시 텍스트 인풋 제공
                    custom_worker = ""
                    if selected_worker == "직접 입력...":
                        custom_worker = st.text_input("새 작업자 이름 입력", placeholder="작업자 성함")
                        
                    input_symptom = st.text_input("증상 및 상태", value=pre_symptom)
                    input_action = st.text_area("조치 및 수리내용", value=pre_action)
                    input_cost = st.number_input("수리 비용(원)", value=int(pre_cost), step=1000)
                    
                    # 사진 첨부 (수리 전후 등)
                    hist_photo1 = st.file_uploader("현장/조치 사진 1", type=["png", "jpg", "jpeg"], key="hp1")
                    hist_photo2 = st.file_uploader("현장/조치 사진 2", type=["png", "jpg", "jpeg"], key="hp2")
                    
                    col_form_btns = st.columns([3, 1])
                    with col_form_btns[0]:
                        submit_hist = st.form_submit_button(submit_label)
                    with col_form_btns[1]:
                        if st.session_state.edit_mode:
                            cancel_edit = st.form_submit_button("취소")
                            if cancel_edit:
                                st.session_state.edit_mode = False
                                st.session_state.edit_history_id = None
                                st.rerun()
                                
                    if submit_hist:
                        # 최종 작업자명 설정
                        final_worker = custom_worker.strip() if selected_worker == "직접 입력..." else selected_worker
                        
                        if final_worker == "선택하세요" or not final_worker:
                            st.error("작업자명을 올바르게 선택하거나 입력해 주세요.")
                        elif not input_symptom or not input_action:
                            st.error("증상 및 조치내용은 필수 입력 사항입니다.")
                        else:
                            # 사진 파일 임시 저장 처리
                            hp1_path = history_data["사진1"] if st.session_state.edit_mode and history_data else ""
                            hp2_path = history_data["사진2"] if st.session_state.edit_mode and history_data else ""
                            
                            # 새 사진 등록 시 기존 사진 대체
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                            if hist_photo1:
                                hp1_path = os.path.join(PHOTOS_DIR, f"hist_{st.session_state.selected_eq_id}_{timestamp}_1.jpg")
                                with open(hp1_path, "wb") as f:
                                    f.write(hist_photo1.getbuffer())
                            if hist_photo2:
                                hp2_path = os.path.join(PHOTOS_DIR, f"hist_{st.session_state.selected_eq_id}_{timestamp}_2.jpg")
                                with open(hp2_path, "wb") as f:
                                    f.write(hist_photo2.getbuffer())
                                    
                            hist_data = {
                                "날짜_시간": input_date.strip(),
                                "작업자명": final_worker,
                                "거래처명": st.session_state.selected_client,
                                "설비ID": st.session_state.selected_eq_id,
                                "증상상태": input_symptom.strip(),
                                "조치_및_수리내용": input_action.strip(),
                                "사진1": hp1_path,
                                "사진2": hp2_path,
                                "금액": float(input_cost)
                            }
                            
                            if st.session_state.edit_mode and st.session_state.edit_history_id:
                                # Update 작업 실행
                                ok, msg = database.update_history(st.session_state.edit_history_id, hist_data)
                                if ok:
                                    st.success(msg)
                                    st.session_state.edit_mode = False
                                    st.session_state.edit_history_id = None
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                # Insert 작업 실행
                                ok, msg = database.add_history(hist_data)
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                                    
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 계기 과거 이력 리스트 (터치 수정 포함)
                st.markdown('<div class="lux-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">📋 과거 점검/수리 이력</div>', unsafe_allow_html=True)
                
                eq_histories = database.get_histories(st.session_state.selected_eq_id)
                if eq_histories:
                    for item in eq_histories:
                        st.markdown(f"""
                        <div class="history-item">
                            <div class="history-header">
                                <span class="history-worker">👤 작업자: {item['작업자명'] or '미지정'}</span>
                                <span>📅 {item['날짜_시간'] or '날짜 정보 없음'}</span>
                            </div>
                            <div class="history-body">
                                <b>[증상]</b> {item['증상상태'] or '-'}<br>
                                <b>[조치]</b> {item['조치_및_수리내용'] or '-'}<br>
                                <b>[금액]</b> {f"{int(item['금액']):,}원" if item['금액'] is not None else '0원'}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 사진 첨부 확인 및 버튼 배치
                        col_h1, col_h2, col_h3 = st.columns([1, 1, 1])
                        if item['사진1'] and os.path.exists(item['사진1']):
                            with col_h1:
                                st.image(item['사진1'], caption="조치 사진1", width=120)
                        if item['사진2'] and os.path.exists(item['사진2']):
                            with col_h2:
                                st.image(item['사진2'], caption="조치 사진2", width=120)
                                
                        # 수정하기 버튼 (터치 시 입력 폼에 갱신)
                        with col_h3:
                            if st.button("✏️ 수정하기", key=f"edit_btn_{item['id']}"):
                                st.session_state.edit_mode = True
                                st.session_state.edit_history_id = item['id']
                                st.rerun()
                else:
                    st.info("이 계기에 등록된 과거 점검 이력이 없습니다.")
                st.markdown('</div>', unsafe_allow_html=True)
