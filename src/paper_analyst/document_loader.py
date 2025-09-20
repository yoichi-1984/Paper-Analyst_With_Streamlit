import os
import fitz  # PyMuPDF
import docx
from pathlib import Path
from paper_analyst import config

def _sanitize_text(text: str) -> str:
    """
    Streamlitの内部プロトコルで問題を起こしうる文字をサニタイズする。
    制御文字や一部の特殊な空白文字などを除去する。
    """
    sanitized_text = "".join(ch for ch in text if ch.isprintable() or ch.isspace())
    sanitized_text = sanitized_text.replace('\u0000', '')
    sanitized_text = sanitized_text.replace('\u2028', '\n')
    sanitized_text = sanitized_text.replace('\u2029', '\n')
    return sanitized_text

def _read_pdf(file_path: Path) -> (str, bool):
    """PDFファイルからテキストを抽出する。テキストの有無も判定する。"""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        is_text_extracted = text.strip() != ""
        return text.strip(), is_text_extracted
    except Exception:
        return "", False

def _read_docx(file_path: Path) -> str:
    """Wordファイル(.docx)からテキストを抽出する。"""
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs]).strip()
    except Exception:
        return ""

def _read_text(file_path: Path) -> str:
    """
    テキストベースのファイルを読み込む。
    複数のエンコーディング候補を試す。
    """
    encodings_to_try = ['utf-8', 'cp932', 'shift_jis', 'euc_jp']
    
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read().strip()
        except UnicodeDecodeError:
            continue
        except Exception:
            return ""
            
    return ""

def load_documents(folder_path: str) -> (list, list):
    """
    指定されたフォルダ内のサポートドキュメントを読み込む。
    巨大なドキュメントは指定された最大文字数で分割する。
    """
    path = Path(folder_path)
    if not path.is_dir():
        return [], [f"エラー: 指定されたパス '{folder_path}' は有効なフォルダではありません。"]

    supported_extensions = {
        ".pdf": _read_pdf,
        ".docx": _read_docx,
        ".txt": _read_text,
        ".md": _read_text,
        ".csv": _read_text,
    }

    documents = []
    warnings = []

    for file_path in path.iterdir():
        if file_path.is_file() and file_path.suffix in supported_extensions:
            handler = supported_extensions[file_path.suffix]
            content = ""
            
            if file_path.suffix == ".pdf":
                content, has_text = handler(file_path)
                if not has_text and file_path.stat().st_size > 0:
                    warnings.append(f"警告: '{file_path.name}' はテキスト情報を含まないスキャン画像PDFの可能性があります。")
            else:
                content = handler(file_path)

            if content:
                # テキストをサニタイズ
                sanitized_content = _sanitize_text(content)
                
                # 巨大なファイルを分割する処理
                if len(sanitized_content) > config.MAX_DOCUMENT_CHARS:
                    warnings.append(f"警告: '{file_path.name}' はサイズが大きいため、複数のキャンバスに分割しました。")
                    
                    chunks = [
                        sanitized_content[i:i + config.MAX_DOCUMENT_CHARS] 
                        for i in range(0, len(sanitized_content), config.MAX_DOCUMENT_CHARS)
                    ]
                    
                    for i, chunk in enumerate(chunks):
                        documents.append({
                            "filename": f"{file_path.name} (Part {i+1})",
                            "content": chunk
                        })
                else:
                    documents.append({
                        "filename": file_path.name,
                        "content": sanitized_content
                    })
            elif file_path.stat().st_size > 0:
                warnings.append(f"警告: '{file_path.name}' からテキストを抽出できませんでした。対応していない形式か、ファイルが破損している可能性があります。")

    if not documents and not warnings:
        warnings.append("指定されたフォルダに読み込み可能なファイルが見つかりませんでした。")
        
    return documents, warnings