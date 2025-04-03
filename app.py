import os
import json
import datetime
from pprint import pprint

import streamlit as st
from dotenv import dotenv_values

# Import the official VideoIndexerClient classes from your VideoIndexerClient folder
from VideoIndexerClient.Consts import Consts
from VideoIndexerClient.VideoIndexerClient import VideoIndexerClient

# Import your custom modules for user management, file upload, annotation, and quality metrics
from src.user_management import login, logout
from src.file_upload import upload_video
from src.annotation_interface import annotation_interface
from src.quality_dashboard import display_quality_metrics, export_metrics


def list_json_files(directory="data/processed"):
    if not os.path.exists(directory):
        os.makedirs(directory)
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".json")]


def save_insights_to_file(insights, base_name):
    processed_dir = "data/processed"
    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir)
    filename = f"{base_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_cloud.json"
    json_path = os.path.join(processed_dir, filename)
    with open(json_path, "w") as f:
        json.dump(insights, f, indent=4)
    return json_path


def main():
    st.title("Oscar-Ready Film Asset Annotation MVP")

    # User login
    username = login()
    if not username:
        st.stop()  # Stop execution if no user is logged in.
    st.write(f"Hello, {username}! You're logged in.")

    # Load configuration from Streamlit secrets
    AccountName = st.secrets["secrets"]["AccountName"]
    ResourceGroup = st.secrets["secrets"]["ResourceGroup"]
    SubscriptionId = st.secrets["secrets"]["SubscriptionId"]

    # Define additional parameters for the ARM-based Video Indexer resource
    ApiVersion = '2024-01-01'
    ApiEndpoint = 'https://api.videoindexer.ai'
    AzureResourceManager = 'https://management.azure.com'

    # Create the constants object required by VideoIndexerClient
    consts = Consts(ApiVersion, ApiEndpoint, AzureResourceManager,
                    AccountName, ResourceGroup, SubscriptionId)

    # Create the Video Indexer Client instance
    client = VideoIndexerClient()

    # Authenticate your account (synchronous method)
    client.authenticate_async(consts)

    # ------------------------------
    # Local Video Upload Flow
    # ------------------------------
    st.subheader("Upload Video from Local File")
    local_video_path = upload_video()  # Uses your file_upload module
    if local_video_path:
        base_name = os.path.splitext(os.path.basename(local_video_path))[0]
        # Generate a unique video name to avoid conflicts (HTTP 409)
        unique_video_name = f"{base_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        # Call file_upload_async synchronously (per the official sample)
        file_video_id = client.file_upload_async(
            local_video_path, video_name=unique_video_name, excluded_ai=[])
        st.success(f"Video ID from file upload: {file_video_id}")
    else:
        st.info("No video file was uploaded.")
        st.stop()

    # Poll for video indexing completion (synchronous method)
    client.wait_for_index_async(file_video_id)
    st.success("Indexing completed for the uploaded video.")

    # Retrieve video insights (synchronous method)
    insights = client.get_video_async(file_video_id)

    # Save insights JSON to a file in data/processed
    saved_json_path = save_insights_to_file(insights, base_name)
    st.success(f"Metadata saved to: {saved_json_path}")

    # ------------------------------
    # Annotation and Quality Metrics
    # ------------------------------
    st.subheader("Annotation")
    json_files = list_json_files()
    if json_files:
        selected_json = st.selectbox("Select metadata JSON file", json_files)
        annotation_interface(selected_json)
    else:
        st.info("No metadata JSON files found in data/processed.")

    st.subheader("Quality Metrics")
    if json_files:
        selected_metrics_json = st.selectbox(
            "Select metadata JSON file for metrics", json_files, key="metrics")
        display_quality_metrics(selected_metrics_json)
        export_metrics(selected_metrics_json)
    else:
        st.info("No metadata JSON files available for metrics.")

    logout()


if __name__ == "__main__":
    main()
