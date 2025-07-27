"""
読書感想フィードバックアプリ (Streamlit)
------------------------------------------------
• Gemini 2.5‑pro/flash いずれも利用可能 (サイドバーで選択)
• 小説生成 → 感想入力 → Gemini によるフィードバック
• CSV で履歴保存 & グラフ表示
"""

import os
import json
import datetime
import streamlit as st
import pandas as pd
import google.generativeai as genai

# ────────────────────────── 設定 ──────────────────────────
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("Gemini API キー(GEMINI_API_KEY)が設定されていません。")
    st.stop()

genai.configure(api_key=API_KEY)

# UI でモデルを選択 (Pro が優先表示)
AVAILABLE_MODELS = [
    ("gemini-2.5-pro",   "💎 Gemini 2.5‑Pro"),
    ("gemini-2.5-flash", "⚡ Gemini 2.5‑Flash"),
]

# ──────────────────── プロンプト定義 ────────────────────
LEVEL_PROMPT = {
    "初級": "日本の小学高学年でも読める 5,000 字程度の物語を日本語で書いて。",
    "中級": "中学生向けに 5,000 字前後の冒険小説を日本語で書いて。",
    "上級": "高校生〜一般向け 5,000 字超の文学的短編小説を日本語で書いて。",
}

FB_TEMPLATE = """
あなたは中学生向け読書感想文の指導者です。
以下の感想文を評価し、次の JSON 形式だけを出力してください。説明は不要。

{{"よかった点": "〜", "改善点": "〜", "スコア": 80}}

感想文:
{text}
"""

# ──────────────────────── 関数群 ────────────────────────
@st.cache_data(show_spinner=False)
def generate_passage(level: str, model_name: str) -> str:
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(LEVEL_PROMPT[level])
    return response.text.strip()

def get_feedback(text: str, model_name: str) -> dict:
    prompt = FB_TEMPLATE.format(text=text)
    model = genai.GenerativeModel(model_name)
    resp = model.generate_content(prompt).text.strip()
    try:
        return json.loads(resp)
    except json.JSONDecodeError:
        return {"よかった点": "解析失敗", "改善点": "形式を確認", "スコア": 0}

# ──────────────────────── Streamlit UI ───────────────────────
st.set_page_config(page_title="読書感想フィードバックアプリ",
                   page_icon="📘", layout="centered")

# --- サイドバー ---
st.sidebar.title("⚙️ 設定")
model_name = st.sidebar.selectbox(
    "🧠 使用する Gemini モデル",
    options=[m[0] for m in AVAILABLE_MODELS],
    format_func=lambda k: dict(AVAILABLE_MODELS)[k],
    index=0,
)
level = st.sidebar.radio("📚 文章レベル", list(LEVEL_PROMPT.keys()), index=0)

st.title("📘 読書感想フィードバックアプリ")

# --- 文章生成 ---
if "passage" not in st.session_state:
    st.session_state.passage = ""

if st.button("📝 文章を生成する", use_container_width=True):
    with st.spinner("AI が文章を生成中..."):
        st.session_state.passage = generate_passage(level, model_name)

st.markdown("## 今日の文章")
if st.session_state.passage:
    st.info(st.session_state.passage)
else:
    st.write("⬆️ サイドバーでレベルを選び、ボタンを押して文章を生成してください。")

# --- 感想入力 & フィードバック ---
user_input = st.text_area("### ✏️ 感想を書いてね",
                          placeholder="例: 主人公に共感した…", height=180)

CSV_PATH = "feedback_log.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH)
else:
    df = pd.DataFrame(columns=["日付", "レベル", "モデル", "感想", "スコア"])

if st.button("💡 フィードバックをもらう", disabled=not st.session_state.passage):
    if not user_input.strip():
        st.warning("感想を入力してください。")
    else:
        with st.spinner("AI が評価中..."):
            fb = get_feedback(user_input, model_name)
        st.success(f"スコア: {fb['スコア']} 点")
        st.write(f"**よかった点**: {fb['よかった点']}")
        st.write(f"**改善点**: {fb['改善点']}")
        # --- ログ保存 ---
        df.loc[len(df)] = [
            datetime.date.today().isoformat(),
            level,
            model_name,
            user_input,
            fb["スコア"],
        ]
        df.to_csv(CSV_PATH, index=False)

# --- 履歴表示 ---
st.markdown("## 📈 スコア履歴")
if df.empty:
    st.info("まだスコアの記録はありません。")
else:
    st.dataframe(df.tail(10), use_container_width=True)
    st.line_chart(df.set_index("日付")["スコア"])

st.caption("© 2025 読書感想フィードバックアプリ – Gemini 2.5 API + Streamlit")
