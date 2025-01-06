from openai import OpenAI
import streamlit as st
import time
import os
from dotenv import load_dotenv
from PIL import Image
import requests
import io
import base64
import smtplib
import datetime
from pyairtable import Table, Base
import streamlit.components.v1 as components
import cloudinary
import cloudinary.uploader
import numpy as np
import pytz

# 1) .env 파일 로드
load_dotenv()
# 2) 환경 변수에서 값 가져오기
openai_api_key = os.getenv("OPENAI_API_KEY")
airtable_api_key = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("BASE_ID")
TABLE_NAME = os.getenv("TABLE_NAME")
api_secret = os.getenv('YOUR_API_SECRET')
api_key = os.getenv('YOUR_API_KEY')
cloud_name = os.getenv('CLOUD_NAME')
#Airtable url
url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

table = Table(airtable_api_key, BASE_ID, TABLE_NAME)

def get_message():
    time.sleep(3)  # 3초간 지연 (예: API 요청 대기)

#시간 조작
timezone = pytz.timezone("Asia/Seoul")
now = datetime.datetime.now(timezone)
formatted_time = now.strftime("%y/%m/%d %I:%M %p")

#창이 열린 시점의 시간 기록
window_open_time = time.time()

# Cloudinary 설정
cloudinary.config(
    cloud_name= cloud_name,
    api_key= api_key,
    api_secret= api_secret
)
# Cloudinary 사용 함수
def upload_to_cloudinary(file, file_name):
    response = cloudinary.uploader.upload(file, public_id=file_name)
    return response["secure_url"]

client = OpenAI(api_key=openai_api_key)
assistant_id = os.getenv("ASSISTANT_ID")

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    thread_id = thread.id
    st.session_state["thread_id"] = thread_id

# code to hide the watermark using CSS
components.html("""
    <style>
    footer {visibility: hidden;}
    </style>
""", height=0)
# #MainMenu to hide the burger menu at the top-right side
# footer to hide the ```made with streamlit``` mark
hide = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        footer:after {content: ''; display: block; position: absolute; bottom: 0; left: 0; height: 0; width: 100%; background: transparent;}
    </style>
"""
st.markdown(hide, unsafe_allow_html=True)

# HTML 및 JavaScript 삽입 뒤로가기 방지
st.components.v1.html("""
<script>
    // 브라우저 히스토리 스택에 현재 상태 추가
    history.pushState(null, null, location.href);
    // 뒤로가기 버튼 이벤트 감지
    window.onpopstate = function () {
        // 모바일 환경인지 확인
        if (/Mobi|Android/i.test(navigator.userAgent)) {
            alert("뒤로가기를 누르셨습니다. 이 페이지를 떠나시겠습니까?");
            // 다시 현재 페이지로 이동
            history.pushState(null, null, location.href);
        }
    };
</script>
""", height=0)  # height=0으로 빈 공간 제거

#챗봇이 run 실행을 명령 받았는지 확인하는 세션
if "chatbot_response" not in st.session_state:
    st.session_state["chatbot_response"] = ''

if "uploaded_files_len" not in st.session_state:
    st.session_state["uploaded_files_len"] = 0

# 이미지 표시 섹션 (사이드바)
with st.sidebar:
    # 추가로 로컬 이미지나 URL 이미지를 표시할 수 있음
    # 로컬 이미지 경로 리스트
    image_paths = [
        os.path.join("file", "원홀과 투홀 차이.png"),
        os.path.join("file", "원홀 수전 리스트.jpg"),
        os.path.join("file", "투홀 수전 리스트.jpg"),
        os.path.join("file", "싱크대 수전 리스트.jpg"),
        os.path.join("file", "샤워기 수전 리스트.jpg"),
    ]
    
    uploaded_files = st.file_uploader(
        "최대 5장까지 업로드 가능합니다.",
        type=["jpg", "png", "jpeg"],
        accept_multiple_files=True
    )

    if uploaded_files:
            print(st.session_state["chatbot_response"],"입니다다")
            print(len(uploaded_files), st.session_state["uploaded_files_len"])
            if len(uploaded_files) > 5 :
                st.error(f"업로드 할 수 없습니다.")
            # 파일 업로드가 진짜 이뤄졌다면 실행
            
            elif len(uploaded_files) > st.session_state["uploaded_files_len"]:
                #한 번에 업로드 된 파일 수
                real_upload_file_N = len(uploaded_files) - st.session_state["uploaded_files_len"]
                # uploaded_files 리스트에 중복값이 존재하는지 확인
                seen = set()
                file_names = [file.name for file in uploaded_files]
                duplicates = set(x for x in file_names if x in seen or seen.add(x))
                # 업로드 된 파일의 url을 저장할 리스트(만약 한 번에 3번 업로드 하는 케이스일 경우 리스트로 담아뒀다가 전부 db로 보내야 한다.)
                uploaded_url_list = []
                if len(duplicates) == 0: # 중복값이 없다면(중복값이 있다는 건 삭제를 진행한 게 아니며, 중복 업로드 한 게 아니라는 뜻)
                    # cloudnary에 들어갈 파일 랜덤 변수 지정
                    for i in range(real_upload_file_N):
                        photo_random_float = str(np.random.random())
                        # 변환 완료
                        uploaded_url = upload_to_cloudinary(uploaded_files[-i-1],photo_random_float)
                        # 업로드 된 파일의 url을 리스트에 추가
                        uploaded_url_list.append(uploaded_url)
                    #테이블에서 대화 중인 thread_id의 테이블들 찾기
                    column_name = "thread_id"
                    desire = st.session_state["thread_id"]
                    formula = f"FIND('{desire[-4:]}', {{{column_name}}})"
                    filtered_records = table.all(formula=formula)
                    # 찾은 테이블의 id만 모아서 리스트로 모으기
                    id_list = [record["id"] for record in filtered_records]
                    for i in range(real_upload_file_N):
                        #현장사진1~8 구분
                        if "photoN" not in st.session_state:
                            st.session_state["photoN"] = 1
                            pn = st.session_state["photoN"]
                        else:
                            st.session_state["photoN"] = st.session_state["photoN"] + 1
                            pn = st.session_state["photoN"]
                        #가장 먼저 태어난 id를 가진 테이블에 업로드한 사진을 업데이트
                        table.update(id_list[-1],{f'현장사진{pn}': uploaded_url_list[i]})
                    print("streamlit에 파일 업로드2")
                    # strealit에 업로드 된 파일 수랑 세션의 내가 지정한 파일 수랑 같게 함
                    st.session_state["uploaded_files_len"] = len(uploaded_files)

    #원홀과 투홀 차이 사진
    st.write("원홀과 투홀 차이")
    image = Image.open(image_paths[0])
    st.image(image, caption=image_paths[0], use_container_width=True)
        
    # 사이드바 메뉴 생성
    selected_category = st.selectbox(
            "아래에서 카테고리를 선택하세요:",
            [
                "싱크대 수전",
                "샤워기 수전",
                "세면대(원홀)",
                "세면대(투홀)",
            ]
    )
    # 선택된 메뉴에 따라 사진 출력
    if selected_category == "싱크대 수전":
            image = Image.open(image_paths[3])
            st.image(image, caption=image_paths[3], use_container_width=True)
    elif selected_category == "샤워기 수전":
            image = Image.open(image_paths[4])
            st.image(image, caption=image_paths[4], use_container_width=True)
    elif selected_category == "세면대(원홀)":
            image = Image.open(image_paths[1])
            st.image(image, caption=image_paths[1], use_container_width=True)
    elif selected_category == "세면대(투홀)":
            image = Image.open(image_paths[2])
            st.image(image, caption=image_paths[2], use_container_width=True)


    
st.markdown("<h1 style='font-size: 30px;'>수전 수리 상담</h1>", unsafe_allow_html=True)
print("시작")
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "어떤 수리가 필요하신가요?\n(예: 수전교체) \n예상 소요 시간: 2분 이내  \n\n 문제 발생 시, 1551-7784로 문의주세요!"}]
    
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])
    
if prompt := st.chat_input():
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()
    
    client = OpenAI(api_key=openai_api_key)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    response = client.beta.threads.messages.create(
        thread_id=st.session_state["thread_id"],
        role="user",
        content=prompt
    )
    
    run = client.beta.threads.runs.create(
        thread_id=st.session_state["thread_id"],
        assistant_id = assistant_id
    )
    
    st.session_state["chatbot_response"] = run.status
    print(st.session_state["chatbot_response"])
    
    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state["thread_id"],
            run_id = run.id
        )
        print("답변 중")
        # 스피너를 이용하여 로딩 애니메이션 표시
        with st.spinner('답변 중...'):
            message = get_message()
        if run.status == 'completed':
            break
        else:
            time.sleep(0.5)
    
    thread_messages = client.beta.threads.messages.list(st.session_state["thread_id"])
    print("답변 중2")
    msg = thread_messages.data[0].content[0].text.value
    
    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant").write(msg)
    
    #st.session_state["chatbot_response"] = ''
    
    table.create({
        'thread_id': st.session_state["thread_id"][-4:],
        '시간': formatted_time,
        '고객': response.content[0].text.value,
        'AI': msg,
        }
    )