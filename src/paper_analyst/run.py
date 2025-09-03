import sys
import subprocess
from pathlib import Path

def start():
    """
    pyproject.tomlの[project.scripts]から呼び出されるエントリーポイント。
    このスクリプトと同じディレクトリにあるmain.pyをStreamlitで実行します。
    """
    try:
        # このファイル (run.py) の絶対パスを取得
        run_py_path = Path(__file__).resolve()
        # main.py の絶対パスを構築
        main_py_path = run_py_path.parent / "main.py"

        if not main_py_path.exists():
            print(f"エラー: main.py が見つかりません: {main_py_path}", file=sys.stderr)
            sys.exit(1)

        # 実行するコマンドを構築
        command = [sys.executable, "-m", "streamlit", "run", str(main_py_path)]
        
        print(f"コマンドを実行します: {' '.join(command)}")
        
        # Streamlitアプリケーションを起動
        subprocess.run(command, check=True)

    except KeyboardInterrupt:
        print("\nアプリケーションを終了します。")
        sys.exit(0)
    except Exception as e:
        print(f"アプリケーションの起動に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    # このスクリプトが直接実行された場合にも対応
    start()
