import os
import shutil
import streamlit as st

CLOUD_DIR = "data/cloud"


def initialize_cloud_storage():
    if not os.path.exists(CLOUD_DIR):
        os.makedirs(CLOUD_DIR)


def upload_file_to_cloud(local_file_path):
    """
    Simulate uploading a file to cloud storage by copying it to a dedicated cloud directory.
    For production, replace this with boto3 S3 integration.
    Returns the simulated cloud path.
    """
    initialize_cloud_storage()
    file_name = os.path.basename(local_file_path)
    cloud_file_path = os.path.join(CLOUD_DIR, file_name)
    try:
        shutil.copy(local_file_path, cloud_file_path)
        st.success(f"File successfully uploaded to cloud: {cloud_file_path}")
        return cloud_file_path
    except Exception as e:
        st.error(f"Cloud upload simulation failed: {e}")
        return None
