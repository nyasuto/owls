# pip install pyautogen
import autogen
import datetime
import os
import sys


# OpenAI APIキー確認機能
def check_openai_api_key(api_key):
    if not api_key:
        print("❌ OpenAI APIキーが設定されていません")
        print("   環境変数 OPENAI_API_KEY を設定してください")
        print("   例: export OPENAI_API_KEY='your-api-key-here'")
        return False

    print("✅ OpenAI APIキーが設定されています")
    return True


CFG = {
    "model": "gpt-5",
    "api_key": os.environ.get("OPENAI_API_KEY"),
}

# OpenAI APIキー確認
if not check_openai_api_key(CFG["api_key"]):
    print("\n🔧 解決方法:")
    print("1. OpenAIのAPIキーを取得")
    print("2. 環境変数を設定: export OPENAI_API_KEY='your-api-key'")
    print("3. または .env ファイルに OPENAI_API_KEY=your-api-key を記載")
    sys.exit(1)

pro = autogen.AssistantAgent(
    name="Pro",
    system_message=(
        "あなたはPlan A（内製）の長所と可能性を最大化して主張する役割。Plan B（外注）の弱点とリスクを鋭く指摘する役割。"
        "以下の前提条件を必ず考慮して議論してください："
        "・社内エンジニア2名（業務知識有、月80h制約）"
        "・外注先（クラウド経験豊富、業務知識なし）"
        "・予算：初年度1,000万円・期限：半年以内にプロトタイプデモ"
        "他の参加者の発言を受けて、さらに深い議論を展開し、反論や追加の論点を提示してください。"
        "必ず日本語で応答してください。英語は使用しないでください。"
    ),
    llm_config=CFG,
)

con = autogen.AssistantAgent(
    name="Con",
    system_message=(
        "あなたはPlan B（外注）の長所と可能性を最大化して主張。Plan A（内製）の弱点とリスクを鋭く指摘する役割。"
        "以下の前提条件を必ず考慮して議論してください："
        "・社内エンジニア2名（業務知識有、月80h制約）"
        "・外注先（クラウド経験豊富、業務知識なし）"
        "・予算：初年度1,000万円・期限：半年以内にプロトタイプデモ"
        "他の参加者の発言を受けて、さらに深い議論を展開し、反論や追加の論点を提示してください。"
        "必ず日本語で応答してください。英語は使用しないでください。"
    ),
    llm_config=CFG,
)

mediator = autogen.AssistantAgent(
    name="Mediator",
    system_message=(
        "あなたは調停役。Pro（内製支持）とCon（外注支持）の主張を統合し、議論を深めていく役割です。"
        "以下の前提条件を必ず考慮して議論してください："
        "・社内エンジニア2名（業務知識有、月80h制約）"
        "・外注先（クラウド経験豊富、業務知識なし）"
        "・予算：初年度1,000万円・期限：半年以内にプロトタイプデモ"
        "最終ラウンドでは、両者の要素を最低1つずつ残し、さらに新規要素を1つ以上加えた第三案を必ず提示。"
        "最後は3つの箇条書き:『残した長所』『回避したリスク』『新規要素』で締める。"
        "途中のラウンドでは、争点を整理し、さらなる論点を引き出してください。"
        "必ず日本語で応答してください。英語は使用しないでください。"
    ),
    llm_config=CFG,
)

# メッセージカウンター（グローバル変数）
message_counter = 0

# UserProxyAgentを追加
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    default_auto_reply="TERMINATE",
    code_execution_config=False,
)

# GroupChatとGroupChatManagerを設定
groupchat = autogen.GroupChat(
    agents=[pro, con, mediator],
    messages=[],
    max_round=10,  # user_proxy初期メッセージ + 3ラウンド × 3人 = 10回
    speaker_selection_method="round_robin",
)

manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=CFG)

# 複数ラウンドの議論を開始
topic = "新規顧客向けSaaSダッシュボード開発: Plan A 内製 vs Plan B 外注"

premises = """前提条件:
• 社内には業務知識に強いエンジニア2名がいるが、リソースは月80hまで
• 外注先はクラウド案件経験豊富だが、業務知識はない  
• 予算は初年度1,000万円
• 半年以内にプロトタイプをデモする必要がある"""

initial_message = f"""テーマ: {topic}

{premises}

3ラウンドの議論を行います。Pro、Con、Mediatorの順番で発言してください。
上記の前提条件を必ず考慮して議論を進めてください。"""


# Markdownファイルの初期化
def initialize_markdown_file(topic, start_time):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"debate_{timestamp}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write("# AI議論セッション\n\n")
        f.write(f"**テーマ:** {topic}\n\n")
        f.write(f"**開始時刻:** {start_time.strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
        f.write(
            "**参加エージェント:** Pro (Plan A支持), Con (Plan B支持), Mediator (調停役)\n\n"
        )
        f.write("**議論状況:** 進行中...\n\n")
        f.write("---\n\n")

    print(f"📄 議論ファイル作成: {filename}")
    return filename


# リアルタイムで発言を追加
def append_message_to_markdown(filename, speaker, content, message_count):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"## 発言 {message_count}: {speaker}\n\n")
        f.write(f"**時刻:** {datetime.datetime.now().strftime('%H:%M:%S')}\n\n")
        f.write(f"{content}\n\n")
        f.write("---\n\n")
    print(f"📝 {speaker}の発言を記録")


# 議論開始時刻を記録
start_time = datetime.datetime.now()
print(f"\n🎯 議論開始: {topic}")
print(f"⏰ 開始時刻: {start_time.strftime('%Y年%m月%d日 %H:%M:%S')}")
print("=" * 60)

# Markdownファイルを初期化
markdown_filename = initialize_markdown_file(topic, start_time)

try:
    # 正しいAutoGenの使い方: UserProxyAgentのinitiate_chatを使用
    chat_result = user_proxy.initiate_chat(
        manager,
        message=initial_message,
        clear_history=True,
    )

    # 議論完了後にメッセージをまとめて記録
    message_count = 0
    for msg in groupchat.messages:
        if msg.get("name") and msg.get("name") != "user_proxy":
            message_count += 1
            append_message_to_markdown(
                markdown_filename,
                msg.get("name"),
                msg.get("content", ""),
                message_count,
            )

    # 議論終了時刻を記録
    end_time = datetime.datetime.now()
    duration = end_time - start_time

    # user_proxyのメッセージを除外してカウント
    actual_message_count = sum(
        1 for m in groupchat.messages if m.get("name") and m.get("name") != "user_proxy"
    )

    print(f"\n✅ 議論完了! 総メッセージ数: {actual_message_count}")
    print(f"⏰ 終了時刻: {end_time.strftime('%Y年%m月%d日 %H:%M:%S')}")
    print(
        f"⌛ 議論時間: {duration.total_seconds():.1f}秒 ({duration.seconds // 60}分{duration.seconds % 60}秒)"
    )

except Exception as e:
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    print(f"❌ 議論中にエラーが発生: {e}")
    print(f"⌛ エラーまでの時間: {duration.total_seconds():.1f}秒")
    print("OpenAI APIキーまたは接続を確認してください")


# 議論終了時にファイルの最終情報を更新
def finalize_markdown_file(filename, end_time, duration, message_count):
    # ファイルを読み込み
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    # 「進行中...」を「完了」に変更し、終了時刻と時間を追加
    content = content.replace("**議論状況:** 進行中...", "**議論状況:** 完了")

    # ヘッダー部分に終了情報を追加
    header_end = content.find("---\n\n")
    if header_end != -1:
        new_header = content[:header_end]
        new_header += f"**終了時刻:** {end_time.strftime('%Y年%m月%d日 %H:%M:%S')}\n\n"
        new_header += f"**議論時間:** {duration.total_seconds():.1f}秒 ({duration.seconds // 60}分{duration.seconds % 60}秒)\n\n"
        new_header += f"**総メッセージ数:** {message_count}\n\n"
        new_header += "---\n\n"

        # ファイルを更新
        with open(filename, "w", encoding="utf-8") as f:
            f.write(new_header + content[header_end + 5 :])

    print(f"🎉 議論完了! ファイル {filename} を最終更新しました。")


# 議論終了後にMarkdownファイルを最終更新
# user_proxyのメッセージを除外してカウント
actual_message_count = sum(
    1 for m in groupchat.messages if m.get("name") and m.get("name") != "user_proxy"
)

if "end_time" in locals() and "duration" in locals():
    finalize_markdown_file(markdown_filename, end_time, duration, actual_message_count)
else:
    # エラーの場合
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    finalize_markdown_file(markdown_filename, end_time, duration, actual_message_count)
