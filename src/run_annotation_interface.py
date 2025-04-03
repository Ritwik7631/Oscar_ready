import streamlit as st
import os
from annotation_interface import annotation_interface

# Set page config must be the first Streamlit command
st.set_page_config(
    layout="wide",
    page_title="Video Keyframe Annotations",
    page_icon="🎬"
)

def main():
    # Path to the metadata file and video file
    metadata_file = "data/processed/LeNeil_20250331214136_cloud.json"
    video_file = "data/raw/LeNeil_20250331214136.mp4"
    
    # Check if metadata file exists
    if not os.path.exists(metadata_file):
        st.error(f"Metadata file not found: {metadata_file}")
        st.info("Please ensure the metadata file exists in the correct location.")
        return
    
    # Check if video file exists
    if not os.path.exists(video_file):
        st.error(f"Video file not found: {video_file}")
        st.info("Please ensure the video file exists in the correct location.")
        return
    
    # Load metadata and add video path
    import json
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    metadata['video_path'] = video_file
    
    # Run the annotation interface
    annotation_interface(metadata)

if __name__ == "__main__":
    main() 