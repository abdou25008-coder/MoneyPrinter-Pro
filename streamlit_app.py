import os
import sys

# Ensure project root is prioritized in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Execute the primary WebUI application
main_script = os.path.join(root_dir, "webui", "Main.py")
if os.path.exists(main_script):
    with open(main_script, "r", encoding="utf-8") as f:
        code = compile(f.read(), main_script, "exec")
        exec(code, globals())
else:
    import streamlit as st
    st.error("مجلد webui غير موجود في المستودع! يرجى التأكد من رفع مجلدي 'webui' و 'app' إلى GitHub.")
