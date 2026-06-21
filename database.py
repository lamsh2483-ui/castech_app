import os
import sqlite3
import pandas as pd

DB_FILE = "castech.db"
EXCEL_FILE = "설비이력 및 점검마스터.xlsx"

def get_connection():
    """SQLite 데이터베이스 연결을 반환합니다."""
    # SQLite가 멀티스레드에서 정상 작동하도록 check_same_thread=False 설정
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    """castech.db가 없는 경우, 엑셀 파일을 읽어 데이터베이스를 초기화합니다."""
    if os.path.exists(DB_FILE):
        return False, "이미 데이터베이스 파일이 존재합니다."
        
    if not os.path.exists(EXCEL_FILE):
        return False, f"초기화에 필요한 엑셀 파일({EXCEL_FILE})이 존재하지 않습니다."
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. 설비마스터 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS 설비마스터 (
                거래처명 TEXT,
                설비ID TEXT PRIMARY KEY,
                설비명 TEXT,
                설치위치 TEXT,
                계측기_IP TEXT,
                인디게이터 TEXT,
                로드셀 TEXT,
                형식 TEXT,
                설치년월 TEXT,
                설비사진1 TEXT,
                설비사진2 TEXT
            )
        """)
        
        # 2. 점검이력 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS 점검이력 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                날짜_시간 TEXT,
                작업자명 TEXT,
                거래처명 TEXT,
                설비ID TEXT,
                증상상태 TEXT,
                조치_및_수리내용 TEXT,
                사진1 TEXT,
                사진2 TEXT,
                금액 REAL
            )
        """)
        conn.commit()
        
        # 3. 설비마스터 데이터 로드 및 마이그레이션
        df_master = pd.read_excel(EXCEL_FILE, sheet_name="설비마스터")
        df_master = df_master.rename(columns={
            "계측기 IP": "계측기_IP"
        })
        
        # NaN 값을 None으로 처리
        df_master = df_master.where(pd.notnull(df_master), None)
        
        for _, row in df_master.iterrows():
            cursor.execute("""
                INSERT OR REPLACE INTO 설비마스터 (
                    거래처명, 설비ID, 설비명, 설치위치, 계측기_IP,
                    인디게이터, 로드셀, 형식, 설치년월, 설비사진1, 설비사진2
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["거래처명"], row["설비ID"], row["설비명"], row["설치위치"], row["계측기_IP"],
                row["인디게이터"], row["로드셀"], row["형식"], row["설치년월"], row["설비사진1"], row["설비사진2"]
            ))
            
        # 4. 전체점검내역 데이터 로드 및 마이그레이션
        df_history = pd.read_excel(EXCEL_FILE, sheet_name="전체점검내역")
        df_history = df_history.where(pd.notnull(df_history), None)
        
        for _, row in df_history.iterrows():
            raw_eq_id = row["설비ID"]
            client_name = row["거래처명"]
            eq_id = raw_eq_id
            
            # 'KCC안성공장: WE-1307' 형태의 데이터를 분리하여 정제
            if raw_eq_id and ":" in str(raw_eq_id):
                parts = str(raw_eq_id).split(":")
                extracted_client = parts[0].strip()
                extracted_eq = parts[1].strip()
                if not client_name:
                    client_name = extracted_client
                eq_id = extracted_eq
                
            # 날짜 형식 처리
            dt_val = str(row["날짜/시간"]) if row["날짜/시간"] else None
            
            cursor.execute("""
                INSERT INTO 점검이력 (
                    날짜_시간, 작업자명, 거래처명, 설비ID, 증상상태, 조치_및_수리내용, 사진1, 사진2, 금액
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dt_val, row["작업자명"], client_name, eq_id, row["증상상태"],
                row["조치 및 수리내용"], row["사진1"], row["사진2"], row["금액"]
            ))
            
        conn.commit()
        conn.close()
        return True, "데이터베이스 초기화 및 엑셀 데이터 마이그레이션이 완료되었습니다."
        
    except Exception as e:
        return False, f"데이터베이스 초기화 실패: {str(e)}"

def get_clients():
    """모든 고유 거래처명 리스트를 가져옵니다."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT 거래처명 FROM 설비마스터 WHERE 거래처명 IS NOT NULL AND 거래처명 != ''")
    clients = [row[0] for row in cursor.fetchall()]
    conn.close()
    return clients

def get_equipments(client_name, search_query=None):
    """특정 거래처에 소속된 계기 목록을 가져옵니다. 검색어가 있으면 필터링합니다."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if search_query:
        # 설비ID 또는 설비명에 검색어가 들어간 데이터 검색
        q = f"%{search_query}%"
        cursor.execute("""
            SELECT * FROM 설비마스터 
            WHERE 거래처명 = ? AND (설비ID LIKE ? OR 설비명 LIKE ?)
            ORDER BY 설비ID
        """, (client_name, q, q))
    else:
        cursor.execute("""
            SELECT * FROM 설비마스터 
            WHERE 거래처명 = ? 
            ORDER BY 설비ID
        """, (client_name,))
        
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_equipment_by_id(eq_id):
    """설비 ID로 단일 설비의 상세 정보를 조회합니다."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM 설비마스터 WHERE 설비ID = ?", (eq_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_equipment(eq_data):
    """신규 계기를 등록합니다."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO 설비마스터 (
                거래처명, 설비ID, 설비명, 설치위치, 계측기_IP,
                인디게이터, 로드셀, 형식, 설치년월, 설비사진1, 설비사진2
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            eq_data.get("거래처명"), eq_data.get("설비ID"), eq_data.get("설비명"), 
            eq_data.get("설치위치"), eq_data.get("계측기_IP"), eq_data.get("인디게이터"), 
            eq_data.get("로드셀"), eq_data.get("형식"), eq_data.get("설치년월"), 
            eq_data.get("설비사진1"), eq_data.get("설비사진2")
        ))
        conn.commit()
        return True, "신규 계기가 성공적으로 등록되었습니다."
    except sqlite3.IntegrityError:
        return False, f"이미 존재하는 설비ID({eq_data.get('설비ID')})입니다."
    except Exception as e:
        return False, f"계기 등록 실패: {str(e)}"
    finally:
        conn.close()

def get_histories(eq_id=None):
    """특정 설비의 과거 점검 이력을 조회합니다. eq_id가 없으면 전체를 조회합니다."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if eq_id:
        cursor.execute("""
            SELECT * FROM 점검이력 
            WHERE 설비ID = ? 
            ORDER BY 날짜_시간 DESC
        """, (eq_id,))
    else:
        cursor.execute("""
            SELECT * FROM 점검이력 
            ORDER BY 날짜_시간 DESC
        """)
        
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_history_by_id(history_id):
    """점검이력 ID로 단일 이력을 조회합니다."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM 점검이력 WHERE id = ?", (history_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_history(history_data):
    """새로운 점검/수리 이력을 등록합니다."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO 점검이력 (
                날짜_시간, 작업자명, 거래처명, 설비ID, 증상상태, 조치_및_수리내용, 사진1, 사진2, 금액
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            history_data.get("날짜_시간"), history_data.get("작업자명"), 
            history_data.get("거래처명"), history_data.get("설비ID"), 
            history_data.get("증상상태"), history_data.get("조치_및_수리내용"), 
            history_data.get("사진1"), history_data.get("사진2"), 
            history_data.get("금액")
        ))
        conn.commit()
        return True, "점검 내역이 성공적으로 등록되었습니다."
    except Exception as e:
        return False, f"점검 내역 등록 실패: {str(e)}"
    finally:
        conn.close()

def update_history(history_id, history_data):
    """기존 점검/수리 이력을 수정합니다."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE 점검이력 SET
                날짜_시간 = ?,
                작업자명 = ?,
                거래처명 = ?,
                설비ID = ?,
                증상상태 = ?,
                조치_및_수리내용 = ?,
                사진1 = ?,
                사진2 = ?,
                금액 = ?
            WHERE id = ?
        """, (
            history_data.get("날짜_시간"), history_data.get("작업자명"), 
            history_data.get("거래처명"), history_data.get("설비ID"), 
            history_data.get("증상상태"), history_data.get("조치_및_수리내용"), 
            history_data.get("사진1"), history_data.get("사진2"), 
            history_data.get("금액"), history_id
        ))
        conn.commit()
        return True, "점검 내역이 성공적으로 수정되었습니다."
    except Exception as e:
        return False, f"점검 내역 수정 실패: {str(e)}"
    finally:
        conn.close()

def get_workers():
    """데이터베이스에서 고유 작업자 목록을 조회합니다."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT 작업자명 FROM 점검이력 
        WHERE 작업자명 IS NOT NULL AND 작업자명 != '' AND 작업자명 != '선택하세요'
        ORDER BY 작업자명
    """)
    workers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return workers

if __name__ == "__main__":
    # 스크립트 단독 실행 시 데이터베이스 초기화 테스트
    success, msg = init_db()
    print(msg)
