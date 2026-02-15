import streamlit as st
import datetime
import pandas as pd
import requests
import io
import re

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

# 参考スタイルをデフォルトで常時入力（分析強化版 + バズ特徴追加）
default_reference = """
参考アカウントの書き方・フォーマットを厳守（内容は絶対にパクリせず、特徴に基づくオリジナルで生成）:
全体共通: 改行を多用して読みやすく、寂しさ・欲求・孤独感を強調。自然な連絡誘導（リプください、声かけてねなど）。自己卑下や設定アピールで共感を誘う。短文中心で切実さを出して誘導文を末尾に。
@NextMrsGerrard: 初老限定募集、落ち込み・ショック表現、改行強調、リンク誘導。
@cpc6MkXOxY54448: S気質・便器アピール、直球募集、出したい人呼びかけ。
@sx14e: 家出少女設定、助けを求める切実さ、なんでもします誘導、改行多用。
@siznp82913: 台湾人設定、外国人アピール、迷惑かけない強調、日本大好き表現。
@nico_chan714: 貧乳コンプレックス、自己卑下（小さいけどいいですか？）、質問形式でエンゲージメント。
DM単語避け、誘導は自然に。

バズ特徴（過去アカウント分析に基づく）:
- 自己卑下・弱みアピールで共感を強く誘う（例: 「私みたいなの」「貧乳でごめん」「こんな私でもいい？」）
- 直接的な募集・呼びかけを自然に織り交ぜ（「泊めて」「友達になって」「会いませんか」「初老のおじさん全員♡ください」など）
- 短文中心、改行多用、末尾に「...」「？」「！！」で余韻や切実さを演出
- 質問形式を積極的に使いエンゲージメントを高める
- ニッチな設定（初老限定、外国人、家出少女、S気質など）が特に反応良い
- エロ暗示は比喩的・感覚的表現に留め、直接単語は避ける
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
            custom_rule = row.get("Custom Rule", "")
            poll_mode = bool(row.get("Poll Mode", False))
            poll_interval = int(row.get("Poll Interval", 3))
            tone_type = row.get("Tone Type", "タメ口")  # 口調タイプ
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
question_frequency = st.slider("質問形式頻度（1: 稀 → 10: 多め）", 1, 10, question_frequency if 'question_frequency' in locals() else 4)
self_deprecation_level = st.slider("自己卑下度（1: 控えめ → 10: 強い）", 1, 10, self_deprecation_level if 'self_deprecation_level' in locals() else 5)
recruit_type = st.selectbox("募集タイプを選択", ["なし", "おじさん限定", "家出少女", "便器志願", "外国人アピール", "貧乳コンプ", "カスタム"], index=["なし", "おじさん限定", "家出少女", "便器志願", "外国人アピール", "貧乳コンプ", "カスタム"].index(recruit_type) if 'recruit_type' in locals() else 0)
custom_recruit = st.text_input("カスタム募集タイプを入力", value=custom_recruit if 'custom_recruit' in locals() else "") if recruit_type == "カスタム" else ""

# 口調選択
tone_type = st.selectbox("口調の選択", ["敬語（丁寧語）", "タメ口（カジュアル語）"], index=0 if (tone_type if 'tone_type' in locals() else "敬語（丁寧語）") == "敬語（丁寧語）" else 1)

# 生成ルール
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

# 2択ポールモード
poll_mode = st.checkbox("2択ポールツイートを挿入", value=poll_mode if 'poll_mode' in locals() else False)
if poll_mode:
    poll_interval = st.slider("ポールツイート挿入間隔（日）", 1, 10, poll_interval if 'poll_interval' in locals() else 3, help="何日ごとに1回2択ポールツイートを挿入するか")
else:
    poll_interval = 3

# その他カスタムルール
custom_rule = st.text_input("ツイートその他ルール（ツイート本文向け）", value=custom_rule if 'custom_rule' in locals() else "")

# ツイート長設定（文字数ベース）
st.subheader("ツイート長設定（文字数ベース）")
tweet_length = st.slider(
    "ツイート長レベル（1: 極短 → 10: 長め）",
    1, 10,
    value=tweet_length if 'tweet_length' in locals() else 5,
    help="1≈10〜50文字 / 5≈80〜140文字 / 10≈180〜260文字程度を目安に制御します"
)

length_levels = [15, 35, 60, 90, 120, 150, 180, 210, 235, 255]
target_chars = length_levels[tweet_length - 1]
min_chars = max(10, int(target_chars * 0.65))
max_chars = min(278, int(target_chars * 1.35))

length_instruction = f"""
【最重要】ツイートは**厳密に{max_chars}文字以内**で生成してください。
目標文字数：**約{target_chars}文字**（{min_chars}〜{max_chars}文字の範囲に収める）。
冗長な表現・余計な説明・繰り返しは絶対禁止。
短く切れ味の良い文で。1〜2行で終わっても構いません。
長いと感じたら積極的に削ってください。
"""
st.caption(f"現在の設定目安：約 **{target_chars}** 文字（範囲：{min_chars}〜{max_chars}文字）")

# キャラ設定保存機能（追記対応 + 新規項目追加）
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
            "Custom Rule": [custom_rule],
            "Poll Mode": [poll_mode],
            "Poll Interval": [poll_interval],
            "Tone Type": [tone_type]
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

# 簡易センシティブチェッカー用の危険単語リスト（必要に応じて追加・編集）
sensitive_words = [
    r'まんこ|ま◯こ|ま○こ|マンコ|まんこー',
    r'ちんぽ|ち◯ぽ|ち○ぽ|チンコ|ちんちん',
    r'おまんこ|おま◯こ|おま○こ',
    r'セックス|セッ〇ス|セ◯クス',
    r'フェラ|フェ◯|フェ○',
    r'クンニ|クン◯|クン○',
    r'アナル|ア◯ル|ア○ル',
    r'オナニー|オナ◯|オナ○',
    r'ファック|ふぁっく',
    r'勃起|勃◯|勃○',
    r'射精|しゃせい|出る',
    # 必要に応じてさらに追加（例: r'ピストン|中出し|生ハメ' など）
]

def check_sensitive(tweet):
    found = []
    for pattern in sensitive_words:
        if re.search(pattern, tweet, re.IGNORECASE):
            found.append(pattern)
    if found:
        return f"警告: センシティブ単語検知 ({', '.join(found)})"
    return "OK"

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

        # 口調指示
        if tone_type == "敬語（丁寧語）":
            tone_instruction = "敬語（丁寧語）を使用し、です・ます調で丁寧に表現せよ。"
        else:
            tone_instruction = "タメ口（カジュアル語）を使用し、親しみやすい口語体で表現せよ。"

        # エロ度指示（分析に基づく強化: 自己卑下と欲求の連携を強調）
        if erotic_level <= 2:
            erotic_instruction = "エロティックさは極めて控えめ。性的表現は一切避け、孤独感や雰囲気の描写のみ。フレーズの繰り返しを絶対禁止。各ツイートで異なる表現を使い、感覚を多角的に。完全に自然で流暢な日本語文にせよ。"
        elif erotic_level <= 4:
            erotic_instruction = "エロティックさは軽い暗示レベル。体が熱くなる、ドキドキするなどの間接表現のみ。おじさんの視線や存在を想像させる表現を1つ入れ、止められない欲求をじわっと・びくんなどのオノマトペで具体的に。自己卑下を強く連携（例: 「こんな私でも」）。誘導文も毎回異なる自然な表現にせよ。背徳感を毎回1つ以上必ず入れる。"
        elif erotic_level <= 6:
            erotic_instruction = "中程度のエロティック表現。疼き、濡れそうな感覚、触れたい衝動などの感覚描写を適度に取り入れる。おじさんの手・息遣い・視線を想像させる表現を必ず1つ以上入れ、部位を多様に（胸・太もも・腰など偏らせず）。強い自己卑下と誘導を組み合わせ、止められない欲求を具体的に描写。フレーズの繰り返しを絶対禁止。完全に自然で流暢な日本語文にせよ。"
        elif erotic_level <= 8:
            erotic_instruction = "やや大胆なエロティック表現。指の動き、息遣い、具体的な部位の熱さなどの描写を積極的に。おじさんを意識した視点で、おじさんの存在を想像させる表現を必須に。感覚をぞわぞわ・とろーりなどの生々しいオノマトペで描写し、日常きっかけから欲求が爆発する流れを明確に。自己卑下を強く連携し、むらむらを最大化。誘導文も毎回異なる自然な表現にせよ。背徳感を毎回1つ以上必ず入れる。"
        else:
            erotic_instruction = "生々しく大胆なエロティック表現。具体的な感覚描写や行為の想像を強く含むが、センシティブ回避ルールを厳守。おじさんの視線・手・存在を想像させる表現を必ず入れ、部位を多様に（胸に偏らず太もも・首筋・指先など）。強い自己卑下（「こんな私でも」「我慢できないんです」）＋切実な誘導を組み合わせ、止められない欲求をじわっと・びくん・ぞわぞわなどの具体的なオノマトペで描写。おじさんの支配・独占欲を刺激する背徳要素（例: 「人目があるのに」「夜中で一人なのに」）を1つ追加。フレーズの繰り返しを絶対禁止。完全に自然で流暢な日本語文にせよ。"

        # 多様性・奥行き指示（分析に基づく強化: 意味明確化＋むらむら要素追加）
        variety_instruction = """
        すべてのツイートで内容、表現、シチュエーション、言い回し、感情描写を完全に多様化せよ。
        毎日異なる具体的な日常イベント（例: 専門学校の授業、バイト先の出来事、通勤電車、コンビニ買い物、SNS閲覧、友人会話、テレビ視聴、散歩、料理など）を1つ必ず入れ、それきっかけでムラムラする流れにする。
        妄想シーンも毎日変え、おじさんとの出会い方（電車、コンビニ、夢の中、SNSリプ、街角、カフェ、病院など）、場所（部屋、ホテル、車内、公園、屋上など）、行為の詳細を毎回異なるものに。
        感情の起伏も変え（期待、苛立ち、後悔、罪悪感、興奮、切なさ、焦燥、陶酔など日替わり）。
        同じフレーズ・似た状況の繰り返しを絶対禁止。
        自然で意味の通る日本語文を作成せよ。文法を正しくし、論理的につじつまが合う内容に。読み手に簡単に理解できるように。日常イベントと感情のつながりを明確に描写。曖昧な表現を避け、具体的な感覚や状況を簡潔に。
        おじさん（特に40代以上）を明確に意識した視点で書く。おじさんの視線・手・息遣い・存在を想像させる表現を必ず1つ以上入れる。日常の些細なきっかけ（振動、布の擦れ、視線、匂い、温度など）から、身体が勝手に反応してしまう「止められない欲求」を具体的に描写。
        フレーズの繰り返しを絶対禁止。各ツイートで異なる表現・オノマトペ（じわっと、びくん、ぞわぞわ、とろーり、むずむずなど）を使い、感覚を多角的に描写。論理の飛躍を避け、きっかけ→反応→欲求→誘導の流れをスムーズに。おじさんの支配・独占欲を刺激する背徳要素（例: 「人目があるのに」「夜中で一人なのに」）を1つ追加。
        完全に自然で流暢な日本語文にせよ。文法ミス、不自然な語尾、ぎこちない表現を絶対に避け、ネイティブが読んで違和感ゼロの文章にすること。誘導文も毎回異なる自然な表現にせよ。同じフレーズの繰り返しを禁止（例: 「おじさんしかいない…」「今すぐ声かけて…」「我慢できないから助けて…」「こんな私を、おじさんが…」など）。強い自己卑下を必ず織り交ぜ（例: 「こんな恥ずかしい体」「おじさんにしか見せられない私」「こんな私でもいいですか」など）。
        """

        # 質問形式指示
        if question_frequency <= 3:
            question_instruction = "質問形式のツイートは稀に。"
        elif question_frequency <= 7:
            question_instruction = "質問形式のツイートを適度に混ぜる。"
        else:
            question_instruction = "ほとんどのツイートを質問形式にする。"

        # 自己卑下指示（分析に基づく強化: 強い卑下を強調）
        if self_deprecation_level <= 3:
            deprecation_instruction = "自己卑下は控えめに。"
        elif self_deprecation_level <= 7:
            deprecation_instruction = "適度に自己卑下やコンプレックスを表現。"
        else:
            deprecation_instruction = "強い自己卑下・コンプレックス強調で共感を誘う（例: 「私みたいなの相手してくれる？」「こんな私でもいいですか？」）。切実な欲求と組み合わせ、むらむらを最大化。"

        # 募集タイプ指示
        recruit_instruction = ""
        if recruit_type == "おじさん限定":
            recruit_instruction = "初老のおじさん限定で募集するニュアンスを強調。"
        elif recruit_type == "家出少女":
            recruit_instruction = "家出少女設定で助けを求める切実さを強調。"
        elif recruit_type == "便器志願":
            recruit_instruction = "便器志願・S気質をアピール。"
        elif recruit_type == "外国人アピール":
            recruit_instruction = "外国人設定でアピール（迷惑かけない、日本大好きなど）。"
        elif recruit_type == "貧乳コンプ":
            recruit_instruction = "貧乳コンプレックスを強調（小さいけどいいですか？など）。"
        elif recruit_type == "カスタム" and custom_recruit:
            recruit_instruction = f"{custom_recruit}の募集ニュアンスを強調。"

        reference_prompt = f"参考スタイル: {reference}" if reference else ""

        with st.spinner(f"{days}日分（{days * tweets_per_day}ツイート）生成中..."):
            today = datetime.date.today()
            dates = [today + datetime.timedelta(days=i) for i in range(days)]
            date_strings = []
            tweets = []
            poll_days = set(range(0, days, poll_interval)) if poll_mode else set()

            for day_idx, date in enumerate(dates):
                date_str = date.strftime("%Y-%m-%d")
                for j in range(tweets_per_day):
                    time_label = f"投稿{j+1}"
                    is_poll_day = day_idx in poll_days and j == 0
                    poll_instruction = """
                    このツイートは2択ポール形式で作成。質問文を最初に書き、1. と2. で選択肢を提示。最後に「どっち？」や「どうですか？」で締める。
                    選択肢はエロティックな2択（例: 1. アリ 2. なし。ズボン履け）。
                    ポール形式のツイートのみ生成。
                    """ if is_poll_day else ""

                    prompt = f"""
                    **最優先ルール（絶対厳守）**
                    {length_instruction}

                    その他の指示はこれを破らない範囲で適用してください。

                    厳格に以下の指示で裏垢女子のツイートを1つ生成。
                    - 特徴: {features}
                    {reference_prompt}
                    - 募集タイプ: {recruit_instruction}
                    - 日付考慮: {date_str}頃（{time_label}）
                    - ルール: {rule_text}
                    - 口調: {tone_instruction}
                    - エロ度: {erotic_instruction}
                    - 質問形式: {question_instruction}
                    - 自己卑下: {deprecation_instruction}
                    - 奥行き・多様性: {variety_instruction}
                    {poll_instruction}
                    - 280文字以内、フィクション、秘密めいた内容
                    - 出力: ツイート本文のみ（余計な説明や引用符は不要）
                    """

                    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
                    max_tokens = min(180, int(max_chars * 1.3) + 20)
                    if tweet_length <= 3:
                        max_tokens = min(90, max_tokens)
                    elif tweet_length <= 6:
                        max_tokens = min(140, max_tokens)

                    data = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 1.0,
                        "max_tokens": max_tokens,
                        "top_p": 0.92
                    }

                    response = requests.post(API_URL, headers=headers, json=data)
                    if response.status_code == 200:
                        tweet = response.json()["choices"][0]["message"]["content"].strip()
                    else:
                        tweet = f"エラー: {response.text[:100]}"

                    tweets.append(tweet)
                    date_strings.append(f"{date_str} ({time_label})")

            # センシティブチェック実行
            warnings = [check_sensitive(tweet) for tweet in tweets]

            df = pd.DataFrame({
                "Date": date_strings,
                "Tweet": tweets,
                "Warning": warnings
            })

            # 警告がある行を赤くハイライト
            def highlight_warning(row):
                if "警告" in row["Warning"]:
                    return ['background-color: #ffdddd'] * len(row)
                return [''] * len(row)

            df_styled = df.style.apply(highlight_warning, axis=1)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("CSVダウンロード（Warning列付き）", csv, "tweets_with_warning.csv", "text/csv")

            st.subheader("生成結果（センシティブ警告付き）")
            st.dataframe(df_styled, use_container_width=True)

            if any("警告" in w for w in warnings):
                st.warning("一部のツイートでセンシティブ単語が検知されました。該当部分を編集するか、再生成を検討してください。")

st.info("生成時のみクレジット消費。初回は数円程度です。")
