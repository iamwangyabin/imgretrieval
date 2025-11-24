import streamlit as st
import os
import tempfile
from PIL import Image
from src.search import SearchEngine
from src.database import get_stats

st.set_page_config(page_title="Local Image Retrieval", layout="wide")

@st.cache_resource
def get_search_engine():
    return SearchEngine()

def main():
    st.title("🔍 Local Image Retrieval System")
    
    # Sidebar
    st.sidebar.header("System Status")
    if st.sidebar.button("Refresh Stats"):
        stats = get_stats()
        st.sidebar.write(stats)
        st.sidebar.info("0: Pending, 1: Processed, 2: Failed")

    # Main Area
    st.write("### Upload an image to search")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"])
    
    if uploaded_file is not None:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.image(uploaded_file, caption="Query Image", use_column_width=True)
            
        with col2:
            with st.spinner("Searching..."):
                # Save uploaded file to temp
                tfile = tempfile.NamedTemporaryFile(delete=False) 
                tfile.write(uploaded_file.read())
                tfile.close()
                
                engine = get_search_engine()
                results = engine.search(tfile.name, k=20)
                
                os.unlink(tfile.name)
                
            if results:
                st.success(f"Found {len(results)} matches.")
                
                # Display results in a grid
                cols = st.columns(5)
                for idx, (path, score) in enumerate(results):
                    with cols[idx % 5]:
                        try:
                            st.image(path, caption=f"Score: {score:.4f}", use_column_width=True)
                            st.caption(os.path.basename(path))
                        except Exception as e:
                            st.error(f"Error loading {path}")
            else:
                st.warning("No matches found.")

if __name__ == "__main__":
    main()
