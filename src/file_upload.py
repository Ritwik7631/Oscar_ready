import streamlit as st
import os

RAW_VIDEO_DIR = "data/raw_videos"


def upload_video():
    """
    Uses Streamlit's file_uploader to upload video files.
    Stores them in data/raw_videos/.
    Returns the file path if successful, otherwise None.
    """
    uploaded_file = st.file_uploader("Upload a video file", type=[
                                     "mp4", "mov", "avi", "mkv"])
    if uploaded_file is not None:
        if not os.path.exists(RAW_VIDEO_DIR):
            os.makedirs(RAW_VIDEO_DIR)
        file_path = os.path.join(RAW_VIDEO_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"File uploaded successfully: {uploaded_file.name}")
        return file_path
    return None
