import os
import sys

# Ensure project root is prioritized in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

webui_dir = os.path.join(root_dir, "webui")
if webui_dir not in sys.path:
    sys.path.insert(0, webui_dir)

main_script = os.path.join(webui_dir, "Main.py")

if os.path.exists(main_script):
    with open(main_script, "r", encoding="utf-8") as f:
        code_content = f.read()

    namespace = globals().copy()
    namespace["__file__"] = main_script
    namespace["__name__"] = "__main__"
    exec(compile(code_content, main_script, "exec"), namespace)
else:
    import streamlit as st
    st.error("مجلد webui غير موجود في المستودع! يرجى التأكد من رفع مجلدي 'webui' و 'app' إلى GitHub.")
