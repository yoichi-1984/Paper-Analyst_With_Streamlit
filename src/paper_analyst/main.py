import os
import sys
import json
import time
from importlib import resources

import streamlit as st
import yaml
import tiktoken
from dotenv import load_dotenv
from openai import AzureOpenAI

# --- ローカルモジュールのインポート ---
try:
    # パッケージとしてインストールされている場合
    from paper_analyst import config, document_loader
except ImportError:
    # 開発時に直接実行する場合のフォールバック
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.dirname(current_dir))
    from paper_analyst import config, document_loader

# --- グローバル変数 ---
PROMPTS = {}

# --- ヘルパー関数 ---

def load_prompts():
    """パッケージ内のprompts.yamlを安全に読み込む"""
    global PROMPTS
    try:
        with resources.open_text("paper_analyst", "prompts.yaml") as f:
            yaml_data = yaml.safe_load(f)
            PROMPTS = yaml_data.get("prompts", {})
    except Exception as e:
        st.error(f"重大なエラー: prompts.yamlの読み込みに失敗しました: {e}")
        st.stop()

def initialize_session_state():
    """セッションステートを一括で初期化する"""
    for key, value in config.SESSION_STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value
    
    # ★★★ 追加: ウィジェットをリセットするためのキーカウンター ★★★
    if 'uploader_key_counter' not in st.session_state:
        st.session_state.uploader_key_counter = 0

def reset_session():
    """セッションを完全にリセットする"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state()
    st.rerun()

def get_token_count(string: str, encoding_name: str = "cl100k_base") -> int:
    """tiktokenを使ってテキストのトークン数を計算する"""
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    except Exception:
        return len(string) // 4

def _clear_session_for_load():
    """st.rerun()を呼ばずにセッションをクリアするヘルパー関数"""
    # ★★★ 修正: キーカウンターを維持する ★★★
    uploader_counter = st.session_state.get('uploader_key_counter', 0)
    
    for key in list(st.session_state.keys()):
        del st.session_state[key]
        
    initialize_session_state()
    st.session_state.uploader_key_counter = uploader_counter


def load_session_from_file(uploaded_file):
    """アップロードされたファイルオブジェクトからセッションを復元する"""
    try:
        session_data = json.load(uploaded_file)
        
        required_keys = ["messages", "loaded_documents", "selected_model"]
        if not all(key in session_data for key in required_keys):
            st.error(config.UITexts.SESSION_FORMAT_ERROR)
            return

        _clear_session_for_load()
        
        st.session_state.messages = session_data["messages"]
        st.session_state.loaded_documents = session_data["loaded_documents"]
        st.session_state.selected_model = session_data["selected_model"]
        
        st.session_state.total_usage = session_data.get("total_usage", config.SESSION_STATE_DEFAULTS["total_usage"].copy())
        st.session_state.load_warnings = session_data.get("load_warnings", [])
        
        st.session_state.app_status = "READY"
        st.session_state.system_role_defined = True
        
        st.success(config.UITexts.SESSION_LOADED_SUCCESS)
        
    except Exception as e:
        st.error(config.UITexts.SESSION_LOAD_ERROR.format(e=e))

def on_upload_change():
    """ファイルがアップロードされたときに呼ばれ、処理フラグを立てる"""
    # ★★★ 修正: 動的なキーを使ってウィジェットの状態を取得 ★★★
    uploader_key = f"session_uploader_widget_{st.session_state.uploader_key_counter}"
    if st.session_state[uploader_key] is not None:
        st.session_state.file_to_process = st.session_state[uploader_key]

# --- UI描画関数 ---

def render_sidebar():
    """サイドバーのUI要素を描画する"""
    with st.sidebar:
        st.header(config.UITexts.SIDEBAR_HEADER)
        
        if st.button(config.UITexts.RESET_BUTTON_LABEL, use_container_width=True, disabled=st.session_state.is_generating):
            reset_session()

        st.header(config.UITexts.SESSION_HEADER)
        
        if st.session_state.app_status == "READY" and st.session_state.messages:
            session_data = {
                "messages": st.session_state.messages,
                "loaded_documents": st.session_state.loaded_documents,
                "selected_model": st.session_state.selected_model,
                "total_usage": st.session_state.total_usage,
                "load_warnings": st.session_state.load_warnings,
            }
            st.download_button(
                label=config.UITexts.DOWNLOAD_SESSION_BUTTON,
                data=json.dumps(session_data, ensure_ascii=False, indent=2),
                file_name=f"session_{int(time.time())}.json",
                mime="application/json",
                use_container_width=True
            )

        # ★★★ 修正: 動的なキーをウィジェットに設定 ★★★
        st.file_uploader(
            label=config.UITexts.UPLOAD_SESSION_LABEL, type="json", 
            key=f"session_uploader_widget_{st.session_state.uploader_key_counter}", 
            on_change=on_upload_change, 
            disabled=st.session_state.is_generating
        )

        st.divider()

        if st.session_state.app_status == "READY":
            st.subheader(config.UITexts.LOADED_CONTENT_HEADER)
            for i, doc in enumerate(st.session_state.loaded_documents):
                with st.expander(f"Canvas-{i+1}: {doc['filename']}"):
                    st.text_area(f"canvas_display_{i}", value=doc['content'], height=200, disabled=True, key=f"canvas_text_{i}")
            
            if st.session_state.load_warnings:
                st.subheader(config.UITexts.WARNINGS_HEADER)
                for warning in st.session_state.load_warnings:
                    st.warning(warning)

        st.divider()
        st.session_state.debug_mode = st.checkbox(
            config.UITexts.DEBUG_MODE_CHECKBOX,
            value=st.session_state.get("debug_mode", False)
        )

def render_initial_setup():
    """アプリの初期設定画面（モデル選択、フォルダ指定）を描画する"""
    st.subheader(config.UITexts.MODEL_SELECT_HEADER)
    model_names_str = os.getenv(config.MODEL_NAMES_KEY, "")
    model_names = [name.strip() for name in model_names_str.split(',') if name.strip()]
    
    if not model_names:
        st.error(f"`{config.DOTENV_PATH}` に `{config.MODEL_NAMES_KEY}` を設定してください。")
        st.stop()
    
    selected_model_index = 0
    if st.session_state.selected_model and st.session_state.selected_model in model_names:
        selected_model_index = model_names.index(st.session_state.selected_model)

    st.session_state.selected_model = st.selectbox(
        "model_selector", options=model_names, index=selected_model_index, label_visibility="collapsed"
    )

    st.subheader(config.UITexts.FOLDER_INPUT_HEADER)
    st.session_state.folder_path = st.text_input(
        "folder_path_input", value=st.session_state.folder_path, help=config.UITexts.FOLDER_INPUT_HELP, label_visibility="collapsed"
    )

    if st.button(config.UITexts.LOAD_BUTTON_LABEL, type="primary", use_container_width=True):
        st.session_state.app_status = "LOADING"
        st.rerun()

def render_system_prompt_setup():
    """AIの役割（システムプロンプト）を設定する画面を描画する"""
    st.subheader(config.UITexts.SYSTEM_PROMPT_HEADER)
    system_prompt_input = st.text_area(
        config.UITexts.SYSTEM_PROMPT_AREA_LABEL, value=PROMPTS.get("system", {}).get("text", ""), height=250
    )
    if st.button(config.UITexts.START_CHAT_BUTTON, type="primary"):
        st.session_state.messages = [{"role": "system", "content": system_prompt_input}]
        st.session_state.system_role_defined = True
        st.rerun()

def render_chat_interface():
    """メインのチャットインターフェースを描画する"""
    st.subheader(config.UITexts.CHAT_CONTEXT_SELECT_HEADER)
    doc_options = [doc['filename'] for doc in st.session_state.loaded_documents]
    
    if 'selected_docs' not in st.session_state:
        st.session_state.selected_docs = doc_options

    st.session_state.selected_docs = st.multiselect(
        "context_selector",
        options=doc_options,
        default=st.session_state.selected_docs,
        label_visibility="collapsed"
    )

    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if st.session_state.last_usage_info:
        usage = st.session_state.last_usage_info
        max_tokens_display = st.session_state.get('max_input_tokens', 'N/A')
        usage_text = (
            f"今回のトークン数: {usage['total_tokens']}/{max_tokens_display} (入力: {usage['input_tokens']}, 出力: {usage['output_tokens']}) | "
            f"累計トークン数: {st.session_state.total_usage['total_tokens']}"
        )
        st.caption(usage_text)

    if st.session_state.is_generating:
        if st.button(config.UITexts.STOP_GENERATION_BUTTON):
            st.session_state.stop_generation = True

    if prompt := st.chat_input(config.UITexts.CHAT_INPUT_PLACEHOLDER, disabled=st.session_state.is_generating):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.is_generating = True
        st.session_state.stop_generation = False
        st.session_state.last_usage_info = None
        st.rerun()

# --- メインアプリケーション ---

def run_app():
    """アプリケーションのメインロジック"""
    st.set_page_config(page_title=config.UITexts.APP_TITLE, layout="wide")
    st.title(config.UITexts.APP_TITLE)

    load_prompts()
    if os.path.exists(config.DOTENV_PATH):
        load_dotenv(dotenv_path=config.DOTENV_PATH)
    initialize_session_state()
    
    render_sidebar()

    if 'file_to_process' in st.session_state and st.session_state.file_to_process is not None:
        uploaded_file = st.session_state.file_to_process
        load_session_from_file(uploaded_file)
        st.session_state.file_to_process = None
        
        # ★★★ 修正: キーカウンターをインクリメントしてウィジェットをリセット ★★★
        st.session_state.uploader_key_counter += 1
        st.rerun()

    if st.session_state.app_status == "INITIAL":
        render_initial_setup()

    elif st.session_state.app_status == "LOADING":
        with st.spinner(config.UITexts.LOADING_SPINNER):
            docs, warnings = document_loader.load_documents(st.session_state.folder_path)
            if len(docs) > config.MAX_DOCUMENTS:
                warnings.append(config.UITexts.MAX_DOCS_WARNING.format(max_docs=config.MAX_DOCUMENTS))
                st.session_state.loaded_documents = docs[:config.MAX_DOCUMENTS]
            else:
                st.session_state.loaded_documents = docs
            st.session_state.load_warnings = warnings
            st.session_state.app_status = "READY"
        st.success(config.UITexts.LOADING_DONE)
        st.rerun()

    elif st.session_state.app_status == "READY":
        
        model_name = st.session_state.selected_model
        model_prefix = model_name.split(" ")[0]
        
        env_vars = {
            'api_key': os.getenv(f"{model_prefix}_{config.AZURE_OPENAI_KEY_NAME}"),
            'azure_endpoint': os.getenv(f"{model_prefix}_{config.AZURE_OPENAI_ENDPOINT_NAME}"),
            'deployment_name': os.getenv(f"{model_prefix}_{config.AZURE_OPENAI_DEPLOYMENT_NAME}"),
            'api_version': os.getenv(f"{model_prefix}_{config.AZURE_OPENAI_API_VERSION_NAME}"),
            'max_input_tokens': os.getenv(f"{model_prefix}_MAX_INPUT_TOKENS"),
        }
        
        missing_vars = [key for key, value in env_vars.items() if not value]
        if missing_vars:
            st.error(config.UITexts.MODEL_CONFIG_ERROR.format(model=model_name))
            st.error(f"不足している設定: {', '.join(missing_vars)}")
            st.stop()
        
        try:
            max_input_tokens = int(env_vars['max_input_tokens'])
            st.session_state.max_input_tokens = max_input_tokens
        except (TypeError, ValueError):
            st.error(f"`{model_name}` の `MAX_INPUT_TOKENS` がenvファイルで正しく設定されていません。")
            st.stop()

        try:
            client = AzureOpenAI(
                api_key=env_vars['api_key'], azure_endpoint=env_vars['azure_endpoint'], api_version=env_vars['api_version']
            )
        except Exception as e:
            st.error(config.UITexts.CLIENT_INIT_ERROR.format(e=e))
            st.stop()
        
        if not st.session_state.system_role_defined:
            render_system_prompt_setup()
        else:
            render_chat_interface()

            if st.session_state.is_generating:
                context_texts = []
                for i, doc in enumerate(st.session_state.loaded_documents):
                    if doc['filename'] in st.session_state.get('selected_docs', []):
                        context_texts.append(
                            f"### 参考資料 (Canvas-{i+1}: {doc['filename']})\n{doc['content']}"
                        )
                combined_context = "\n\n---\n\n".join(context_texts)

                messages_for_api = [msg.copy() for msg in st.session_state.messages]
                last_user_message = messages_for_api[-1]["content"]
                
                contextual_prompt = (
                    f"{combined_context}\n\n---\n\n"
                    f"上記の参考資料に基づいて、以下の質問に答えてください。\n\n"
                    f"質問: {last_user_message}"
                )
                messages_for_api[-1]["content"] = contextual_prompt
                
                if st.session_state.get("debug_mode", False):
                    with st.expander(config.UITexts.DEBUG_PROMPT_HEADER, expanded=False):
                        st.text(json.dumps(messages_for_api, indent=2, ensure_ascii=False))

                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    full_response = ""
                    input_tokens = 0
                    
                    try:
                        messages_json_string = json.dumps(messages_for_api)
                        input_tokens = get_token_count(messages_json_string)

                        if input_tokens > max_input_tokens:
                            raise ValueError(
                                f"入力トークン数 ({input_tokens}) が、選択されたモデル ({model_name}) の"
                                f"最大値 ({max_input_tokens}) を超えています。文献を減らすか、質問を短くしてください。"
                            )

                        stream = client.chat.completions.create(
                            model=env_vars['deployment_name'], messages=messages_for_api, max_completion_tokens=2000, stream=True
                        )
                        for chunk in stream:
                            if st.session_state.stop_generation:
                                st.warning(config.UITexts.GENERATION_STOPPED_WARNING)
                                break
                            
                            if chunk.choices and chunk.choices[0].delta.content is not None:
                                full_response += chunk.choices[0].delta.content
                                placeholder.markdown(full_response + "▌")
                    
                    except ValueError as ve:
                        st.error(str(ve))
                    except Exception as e:
                        st.error(f"API呼び出しでエラーが発生しました: {e}")
                    
                    finally:
                        placeholder.markdown(full_response)
                        st.session_state.is_generating = False
                        st.session_state.stop_generation = False
                        
                        if full_response:
                            st.session_state.messages.append({"role": "assistant", "content": full_response})

                            output_tokens = get_token_count(full_response)
                            total_tokens = input_tokens + output_tokens
                            
                            usage_info = { "total_tokens": total_tokens, "input_tokens": input_tokens, "output_tokens": output_tokens }
                            st.session_state.last_usage_info = usage_info

                            st.session_state.total_usage["input_tokens"] += input_tokens
                            st.session_state.total_usage["output_tokens"] += output_tokens
                            st.session_state.total_usage["total_tokens"] += total_tokens
                        
                        st.rerun()

if __name__ == "__main__":
    run_app()

