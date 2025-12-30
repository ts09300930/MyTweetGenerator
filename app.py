import streamlit as st
import datetime
import pandas as pd
import requests

st.title("裏垢女子ツイート生成ツール")

# APIキー管理
if "GROK_API_KEY" in st.secrets:
    API_KEY = st.secrets["GROK_API_KEY"]
else:
    API_KEY = st.text_input("Grok APIキー（ローカルテスト用）", type="password")

API_URL = "https://api.x.ai/v1/chat/completions"

# モデル選択
model_options = [
    "grok-4-1-fast-reasoning (低コスト・推奨)",
    "grok-4-1-fast-non-reasoning",
    "grok-4-fast-reasoning",
    "grok-4 (高性能・高コスト)"
]
selected_model = st.selectbox("使用モデルを選択", model_options, index=0)
model_name = selected_model.split(" (")[0]

# UI入力
features = st.text_area(
    "裏垢女子の特徴を入力",
    placeholder="例: 20代後半OL、欲求不満、エロティックな日常吐露",
    height=150
)

# 参考スタイルをデフォルトで常時入力（最新分析に基づく強化版）
default_reference = """
参考アカウントの書き方・フォーマットを厳守（内容は絶対にパクリせず、特徴に基づくオリジナルで生成）:
全体共通: 改行を多用して読みやすく、寂しさ・欲求・孤独感を強調。自然な連絡誘導（リプください、声かけてねなど）。自己卑下や設定アピールで共感を誘う。
@NextMrsGerrard: 初老のおじさん限定募集、落ち込み表現、改行で強調、リンク誘導。
@cpc6MkXOxY54448: S気質・便器アピール、直球募集、短文で出したい人呼びかけ。
@sx14e: 家出少女設定、助けを求める切実さ、なんでもします誘導、改行多用。
@siznp82913: 台湾人設定、外国人アピール、迷惑かけない強調、日本大好き表現。
@nico_chan714: 貧乳コンプレックス、自己卑下（小さいけどいいですか？）、質問形式でエンゲージメント。
その他: 短文中心、寂しさ強調、誘導文を自然に末尾配置。DM単語避け。
"""

reference = st.text_area(
    "参考スタイル（オプション）\nXアカウントURLや過去ツイート例を貼り付け",
    value=default_reference,  # 常時デフォルト入力
    height=300
)

days = st.slider("生成日数", 1, 60, 30)
tweets_per_day = st.slider("1日あたりのツイート数", 1, 5, 2)

st.subheader("エロ度調整")
erotic_level = st.slider("エロ度（1: 控えめ → 10: 生々しい）", min_value=1, max_value=10, value=5)

st.subheader("ツイート長調整")
tweet_length = st.slider("ツイート長（1: 短め → 10: 長め）", min_value=1, max_value=10, value=6)

st.subheader("生成ルール")
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
emoji_ban = col1.checkbox("絵文字禁止", value=True)  # デフォルトオン
hashtag_ban = col2.checkbox("ハッシュタグ禁止", value=True)  # デフォルトオン
newline_allow = col3.checkbox("改行を適切に使用", value=True)
newline_ban = col4.checkbox("改行完全禁止", value=False)
dm_invite = col5.checkbox("連絡誘導を入れる", value=False)
sensitive_avoid = col6.checkbox("センシティブ回避（暗示表現）", value=True)
fuzzy_mode = col7.checkbox("伏字モード", value=False)

custom_rule = st.text_input("その他ルール")

# （以降の生成部分は以前の完全版と同じ、変更なし）

# ... (省略、以前のコードの生成開始以降をそのままコピー)

st.info("生成時のみクレジット消費。初回は数円程度です。")
