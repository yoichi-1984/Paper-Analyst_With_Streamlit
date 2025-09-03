import os
import fitz  # PyMuPDF
import docx
from pathlib import Path

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
    複数のエンコーディング候補を試し、UnicodeDecodeErrorを回避する。
    """
    # 日本語環境で一般的なエンコーディングを優先的に試すリスト
    encodings_to_try = ['utf-8', 'cp932', 'shift_jis', 'euc_jp']
    
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read().strip()
        except UnicodeDecodeError:
            # デコードに失敗した場合、次のエンコーディングを試す
            continue
        except Exception:
            # その他の予期せぬエラーが発生した場合は空文字を返す
            return ""
            
    # 全てのエンコーディングで失敗した場合
    return ""

def load_documents(folder_path: str) -> (list, list):
    """
    指定されたフォルダを探索し、サポートされているドキュメントを個別に読み込む。
    各ファイルの読み込み結果を検証し、詳細な警告を生成する。
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
                documents.append({
                    "filename": file_path.name,
                    "content": content
                })
            elif file_path.stat().st_size > 0: # ファイルサイズが0より大きいのに内容が空の場合
                 warnings.append(f"警告: '{file_path.name}' からテキストを抽出できませんでした。対応していない形式か、ファイルが破損している可能性があります。")

    if not documents and not warnings:
        warnings.append("指定されたフォルダに読み込み可能なファイルが見つかりませんでした。")
        
    return documents, warnings

