import streamlit as st
import datetime
import pandas as pd
import requests
import io

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

# 参考スタイルをデフォルトで常時入力（分析強化版）
default_reference = """
参考アカウントの書き方・フォーマットを厳守（内容は絶対にパクリせず、特徴に基づくオリジナルで生成）:
全体共通: 改行を多用して読みやすく、寂しさ・欲求・孤独感を強調。自然な連絡誘導（リプください、声かけてねなど）。自己卑下や設定アピールで共感を誘う。短文中心で切実さを出して誘導文を末尾に。
@NextMrsGerrard: 初老限定募集、落ち込み・ショック表現、改行強調、リンク誘導。
@cpc6MkXOxY54448: S気質・便器アピール、直球募集、出したい人呼びかけ。
@sx14e: 家出少女設定、助けを求める切実さ、なんでもします誘導、改行多用。
@siznp82913: 台湾人設定、外国人アピール、迷惑かけない強調、日本大好き表現。
@nico_chan714: 貧乳コンプレックス、自己卑下（小さいけどいいですか？）、質問形式でエンゲージメント。
DM単語避け、誘導は自然に。
"""

# CSV読み込み機能（キャラ選択）
uploaded_csv = st.file_uploader("保存したCSVからキャラ設定を読み込み", type=["csv"])
if uploaded_csv is not None:
    try:
        df_loaded = pd.read_csv(uploaded_csv)
        char_names = ["新規作成"] + df_loaded["Character Name"].dropna().unique().tolist()
        selected_char = st.selectbox("キャラを選択して設定を復元", char_names)
        if selected_char != "新規作成":
            row = df_loaded[df_loaded["Character Name"] == selected_char].iloc[0]
            features = row["Features"]
            reference = row["Reference"]
            days = int(row["Days"])
            tweets_per_day = int(row["Tweets Per Day"])
            erotic_level = int(row["Erotic Level"])
            tweet_length = int(row["Tweet Length"])
            question_frequency = int(row["Question Frequency"])
            self_deprecation_level = int(row["Self Deprecation Level"])
            recruit_type = row["Recruit Type"]
            custom_recruit = row["Custom Recruit"] if pd.notna(row["Custom Recruit"]) else ""
            emoji_ban = bool(row["Emoji Ban"])
            hashtag_ban = bool(row["Hashtag Ban"])
            newline_allow = bool(row["Newline Allow"])
            newline_ban = bool(row["Newline Ban"])
            dm_invite = bool(row["DM Invite"])
            sensitive_avoid = bool(row["Sensitive Avoid"])
            fuzzy_mode = bool(row["Fuzzy Mode"])
            ellipsis_end = bool(row["Ellipsis End"])
            dom_s_mode = bool(row["Dom S Mode"])
            generate_image_prompt = bool(row["Generate Image Prompt"])
            image_prompt_lang = row["Image Prompt Lang"]
            mask_on = bool(row["Mask On"])
            mirror_selfie_mode = row.get("Mirror Selfie Mode", "顔が映る・スマホ映り込み")
            custom_rule = row.get("Custom Rule", "")
            image_custom_prompt = row.get("Image Custom Prompt", "")
            st.success(f"{selected_char}の設定を復元しました")
    except Exception as e:
        st.error(f"CSV読み込みエラー: {e}")
else:
    selected_char = "新規作成"

# UI入力（読み込み値またはデフォルト）
features = st.text_area("裏垢女子の特徴を入力", value=features if 'features' in locals() else "", placeholder="例: 20代後半OL、欲求不満、エロティックな日常吐露", height=150)
reference = st.text_area("参考スタイル（オプション）\nXアカウントURLや過去ツイート例を貼り付け", value=reference if 'reference' in locals() else default_reference, height=300)
days = st.slider("生成日数", 1, 60, days if 'days' in locals() else 30)
tweets_per_day = st.slider("1日あたりのツイート数", 1, 5, tweets_per_day if 'tweets_per_day' in locals() else 2)
erotic_level = st.slider("エロ度（1: 控えめ → 10: 生々しい）", 1, 10, erotic_level if 'erotic_level' in locals() else 5)
tweet_length = st.slider("ツイート長（1: 2行程度 → 10: 8〜10行）", 1, 10, tweet_length if 'tweet_length' in locals() else 6)
question_frequency = st.slider("質問形式頻度（1: 稀 → 10: 多め）", 1, 10, question_frequency if 'question_frequency' in locals() else 4)
self_deprecation_level = st.slider("自己卑下度（1: 控えめ → 10: 強い）", 1, 10, self_deprecation_level if 'self_deprecation_level' in locals() else 5)
recruit_type = st.selectbox("募集タイプを選択", ["なし", "おじさん限定", "家出少女", "便器志願", "外国人アピール", "貧乳コンプ", "カスタム"], index=["なし", "おじさん限定", "家出少女", "便器志願", "外国人アピール", "貧乳コンプ", "カスタム"].index(recruit_type) if 'recruit_type' in locals() else 0)
custom_recruit = st.text_input("カスタム募集タイプを入力", value=custom_recruit if 'custom_recruit' in locals() else "") if recruit_type == "カスタム" else ""
# 生成ルール（2行配置で縦長改善）
st.subheader("生成ルール")
row1 = st.columns(5)
row2 = st.columns(5)
emoji_ban = row1[0].checkbox("絵文字禁止", value=emoji_ban if 'emoji_ban' in locals() else True)
hashtag_ban = row1[1].checkbox("ハッシュタグ禁止", value=hashtag_ban if 'hashtag_ban' in locals() else True)
newline_allow = row1[2].checkbox("改行を適切に使用", value=newline_allow if 'newline_allow' in locals() else True)
newline_ban = row1[3].checkbox("改行完全禁止", value=newline_ban if 'newline_ban' in locals() else False)
dm_invite = row1[4].checkbox("連絡誘導を入れる", value=dm_invite if 'dm_invite' in locals() else False)
sensitive_avoid = row2[0].checkbox("センシティブ回避（暗示表現）", value=sensitive_avoid if 'sensitive_avoid' in locals() else True)
fuzzy_mode = row2[1].checkbox("伏字モード", value=fuzzy_mode if 'fuzzy_mode' in locals() else False)
ellipsis_end = row2[2].checkbox("末尾に。。や...を入れる", value=ellipsis_end if 'ellipsis_end' in locals() else True)
dom_s_mode = row2[3].checkbox("ドSモード", value=dom_s_mode if 'dom_s_mode' in locals() else False)
mirror_selfie_mode = row2[4].radio("鏡自撮りモード", ["オフ", "顔が映る・スマホ映り込み", "顔が映る・スマホ映らない", "顔が映らない・スマホ映らない"], index=["オフ", "顔が映る・スマホ映り込み", "顔が映る・スマホ映らない", "顔が映らない・スマホ映らない"].index(mirror_selfie_mode) if 'mirror_selfie_mode' in locals() else 1)

generate_image_prompt = st.checkbox("ツイート連動画像プロンプトを作成", value=generate_image_prompt if 'generate_image_prompt' in locals() else True)
image_prompt_lang = st.selectbox("プロンプト言語", ["English", "Japanese"], index=0 if ('image_prompt_lang' in locals() and image_prompt_lang == "English") else 1)
mask_on = st.checkbox("白いマスク着用を追加", value=mask_on if 'mask_on' in locals() else True)

# ツイートと画像のルールを分離
custom_rule = st.text_input("ツイートその他ルール（ツイート本文向け）", value=custom_rule if 'custom_rule' in locals() else "")
image_custom_prompt = st.text_input("画像プロンプト追加指示（画像向け）", value=image_custom_prompt if 'image_custom_prompt' in locals() else "", placeholder="例: 夜の部屋背景、上半身のみ、笑顔、薄暗い照明")

# キャラ設定CSV保存機能（追記対応 + 新規項目追加）
st.subheader("キャラ設定保存")
char_name_save = st.text_input("保存するキャラ名（新規または既存）")
if st.button("現在の設定をCSVに追加保存"):
    if char_name_save:
        new_data = {
            "Character Name": [char_name_save],
            "Features": [features],
            "Reference": [reference],
            "Days": [days],
            "Tweets Per Day": [tweets_per_day],
            "Erotic Level": [erotic_level],
            "Tweet Length": [tweet_length],
            "Question Frequency": [question_frequency],
            "Self Deprecation Level": [self_deprecation_level],
            "Recruit Type": [recruit_type],
            "Custom Recruit": [custom_recruit],
            "Emoji Ban": [emoji_ban],
            "Hashtag Ban": [hashtag_ban],
            "Newline Allow": [newline_allow],
            "Newline Ban": [newline_ban],
            "DM Invite": [dm_invite],
            "Sensitive Avoid": [sensitive_avoid],
            "Fuzzy Mode": [fuzzy_mode],
            "Ellipsis End": [ellipsis_end],
            "Dom S Mode": [dom_s_mode],
            "Generate Image Prompt": [generate_image_prompt],
            "Image Prompt Lang": [image_prompt_lang],
            "Mask On": [mask_on],
            "Mirror Selfie Mode": [mirror_selfie_mode],
            "Custom Rule": [custom_rule],
            "Image Custom Prompt": [image_custom_prompt]  # 新規追加
        }
        df_new = pd.DataFrame(new_data)
        csv_new = df_new.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="CSVダウンロード（現在のキャラ追加）",
            data=csv_new,
            file_name="characters_all.csv",
            mime="text/csv"
        )
        st.success("現在の設定をCSVに追加保存しました（ファイル名固定: characters_all.csv）。既存CSVとマージしてご利用ください")
    else:
        st.error("キャラ名を入力してください")

# 生成開始
if st.button("生成開始"):
    if not features or not API_KEY:
        st.error("特徴とAPIキーを入力してください")
    else:
        rule_text = ""
        if emoji_ban: rule_text += "絵文字は一切使用禁止。"
        if hashtag_ban: rule_text += "ハッシュタグは一切使用禁止。"
        if newline_ban: rule_text += "改行は一切使用禁止。"
        if newline_allow: rule_text += "自然で読みやすい位置に適度な改行を挿入（2-4行程度）。"
        if dm_invite: rule_text += "ツイート末尾に自然な連絡誘導文を入れる（例: 「気になったら声かけてね」「リプください」「連絡待ってる」など。「DM」という単語は絶対に使わない）。"
        if sensitive_avoid: rule_text += "Xのセンシティブ判定を回避するため、直接的な性器名・行為名は一切使わず、暗示的・比喩・感覚的な表現のみで描写（例: 「濡れる」→「熱が溢れる」「とろけそう」）。"
        if fuzzy_mode: rule_text += "センシティブな言葉は伏字化（例: ま◯こ、ち◯ぽ、おっぱ◯）またはマイルド表現に置き換え。"
        if ellipsis_end: rule_text += "ツイートの末尾や文中に「。。」「...」「．．．」などを適度に使用して余韻や切なさを演出。"
        if dom_s_mode: rule_text += "ドSな口調で上から目線・言葉責め・煽りを積極的に使用（例: 「おじさんならどうするの？」「満足させられる人だけ来て」など）。"
        rule_text += custom_rule

        # ... (エロ度、ツイート長、重複禁止などの指示は変更なし)

        # 画像プロンプト生成（画像専用指示追加）
        image_prompt = ""
        if generate_image_prompt:
            image_prompt_lang_text = "English" if image_prompt_lang == "English" else "Japanese"
            mask_text = "wearing a white surgical face mask covering nose and mouth," if mask_on else ""
            if mirror_selfie_mode == "顔が映る・スマホ映り込み":
                mirror_text = "taking a mirror selfie in front of a mirror, holding iPhone smartphone with one hand, full body or upper body visible in reflection,"
            elif mirror_selfie_mode == "顔が映る・スマホ映らない":
                mirror_text = "mirror selfie in front of a mirror, face visible but smartphone not in frame, like taken from outside, realistic composition,"
            elif mirror_selfie_mode == "顔が映らない・スマホ映らない":
                mirror_text = "mirror selfie in front of a mirror, face hidden or cropped, body visible, smartphone not in frame, anonymous style,"
            else:
                mirror_text = ""
            photo_style = "photorealistic, high resolution photo, natural indoor lighting, candid selfie style like taken with smartphone camera, realistic skin texture, detailed eyes and hair, style inspired by @BeaulieuEv74781's self-photos but original composition"
            image_prompt_prompt = f"""
            このツイート '{tweet}' に連動したX投稿用画像の詳細なプロンプトを作成。
            - スタイル: {photo_style}
            - Twitterセンシティブに引っかからない程度のエロさ（暗示的、服着用、雰囲気重視）
            - 言語: {image_prompt_lang_text}
            - 必ず含む: Japanese woman, age (estimated from {features}), breast size (estimated from {features}), {mask_text}{mirror_text}
            - 追加指示: {image_custom_prompt}
            - 出力: プロンプト本文のみ
            """
            # ... (API呼び出しは変更なし)

# ... (生成ループ以降は変更なし)

st.info("生成時のみクレジット消費。初回は数円程度です。")
