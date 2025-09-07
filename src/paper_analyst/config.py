# --- 定数定義 ---
DOTENV_PATH = "env/analyst.env"
MAX_DOCUMENTS = 10

# --- 環境変数キー名 ---
MODEL_NAMES_KEY = "MODEL_NAMES"
AZURE_OPENAI_KEY_NAME = "AZURE_OPENAI_KEY"
AZURE_OPENAI_ENDPOINT_NAME = "AZURE_OPENAI_ENDPOINT"
AZURE_OPENAI_DEPLOYMENT_NAME = "AZURE_OPENAI_DEPLOYMENT"
AZURE_OPENAI_API_VERSION_NAME = "AZURE_OPENAI_API_VERSION"

# --- Streamlit セッションステートのデフォルト値 ---
SESSION_STATE_DEFAULTS = {
    "app_status": "INITIAL",
    "selected_model": None,
    "folder_path": "paper",
    "loaded_documents": [],
    "load_warnings": [],
    "messages": [],
    "system_role_defined": False,
    "total_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    "is_generating": False,
    "stop_generation": False,
    "last_usage_info": None,
    "debug_mode": False,  # ★★★ 追加: デバッグモードの状態 ★★★
}

# --- UIに表示されるテキスト ---
class UITexts:
    APP_TITLE = "📄 Paper-Analyst with Streamlit"
    SIDEBAR_HEADER = "設定"
    RESET_BUTTON_LABEL = "セッションをリセット"
    
    # --- デバッグモード ---
    DEBUG_MODE_CHECKBOX = "デバッグモードを有効にする" # ★★★ 追加 ★★★
    DEBUG_PROMPT_HEADER = "デバッグ情報: AIへの最終入力プロンプト" # ★★★ 追加 ★★★
    
    # --- セッション管理 ---
    SESSION_HEADER = "セッション管理"
    DOWNLOAD_SESSION_BUTTON = "会話履歴を保存"
    UPLOAD_SESSION_LABEL = "会話履歴を読み込み"
    SESSION_LOADED_SUCCESS = "会話履歴を読み込みました。"
    SESSION_LOAD_ERROR = "JSON の読み込みに失敗しました: {e}"
    SESSION_FORMAT_ERROR = "対応していないJSONフォーマットです。"

    # --- 初期設定画面 ---
    MODEL_SELECT_HEADER = "1. AIモデルを選択（GPT4.1:文書量重視、o4-mini：思考重視）"
    FOLDER_INPUT_HEADER = "2. 読み込む文献フォルダを指定"
    FOLDER_INPUT_HELP = "仮想環境からの相対パス、またはフルパスで指定します。"
    LOAD_BUTTON_LABEL = "文献を読み込む"
    
    # --- 読み込み処理 ---
    LOADING_SPINNER = "文献を読み込んでいます..."
    LOADING_DONE = "文献の読み込みが完了しました。"
    MAX_DOCS_WARNING = "最大読み込み数 ({max_docs}件) を超えたため、最初の{max_docs}件のみを読み込みました。"

    # --- サイドバー (読み込み後) ---
    LOADED_CONTENT_HEADER = "読み込んだ文献"
    WARNINGS_HEADER = "読み込み時の警告"

    # --- システムプロンプト設定 ---
    SYSTEM_PROMPT_HEADER = "AIの役割（システムプロンプト）を設定"
    SYSTEM_PROMPT_AREA_LABEL = "AIの役割"
    START_CHAT_BUTTON = "この役割でチャットを開始する"

    # --- チャット画面 ---
    CHAT_CONTEXT_SELECT_HEADER = "分析対象の文献を選択"
    CHAT_CONTEXT_SELECT_PLACEHOLDER = "分析に含める文献を選んでください"
    STOP_GENERATION_BUTTON = "生成を停止"
    CHAT_INPUT_PLACEHOLDER = "文献に関する質問を入力..."
    GENERATION_STOPPED_WARNING = "ユーザーによって応答の生成が中断されました。"

    # --- エラーメッセージ ---
    MODEL_CONFIG_ERROR = "モデル '{model}' の設定が不完全です。"
    CLIENT_INIT_ERROR = "Azure OpenAIクライアントの初期化に失敗しました: {e}"

