import os
import json
import requests
from urllib.parse import urljoin
from dotenv import load_dotenv

def download_thumbnails(metadata_file, account_id, video_id, access_token):
    """
    Downloads thumbnails from Azure Video Indexer and saves them to a thumbnails directory.
    
    Args:
        metadata_file (str): Path to the metadata JSON file
        account_id (str): Azure Video Indexer account ID
        video_id (str): Video ID from Azure Video Indexer
        access_token (str): Access token for Azure Video Indexer API
    """
    # Create thumbnails directory if it doesn't exist
    thumbnails_dir = "thumbnails"
    os.makedirs(thumbnails_dir, exist_ok=True)
    
    # Load metadata
    with open(metadata_file, "r") as f:
        metadata = json.load(f)
    
    # Get video insights
    video_insights = metadata.get("videos", [{}])[0].get("insights", {})
    
    # Base URL for Azure Video Indexer API
    base_url = f"https://api.videoindexer.ai"
    
    # Track downloaded thumbnails to avoid duplicates
    downloaded_thumbnails = set()
    
    # Extract and download thumbnails from shots
    for shot in video_insights.get("shots", []):
        for keyframe in shot.get("keyFrames", []):
            for instance in keyframe.get("instances", []):
                thumbnail_id = instance.get("thumbnailId")
                if thumbnail_id and thumbnail_id not in downloaded_thumbnails:
                    # Construct the thumbnail URL
                    thumbnail_url = f"{base_url}/westus2/Accounts/{account_id}/Videos/{video_id}/Thumbnails/{thumbnail_id}"
                    print(f"Trying URL: {thumbnail_url}")
                    
                    # Add authorization header
                    headers = {
                        "Authorization": f"Bearer {access_token}"
                    }
                    
                    try:
                        # Download the thumbnail
                        response = requests.get(thumbnail_url, headers=headers)
                        response.raise_for_status()
                        
                        # Save the thumbnail
                        thumbnail_path = os.path.join(thumbnails_dir, f"{thumbnail_id}.jpg")
                        with open(thumbnail_path, "wb") as f:
                            f.write(response.content)
                        
                        downloaded_thumbnails.add(thumbnail_id)
                        print(f"Downloaded thumbnail: {thumbnail_id}")
                        
                    except Exception as e:
                        print(f"Error downloading thumbnail {thumbnail_id}: {e}")
    
    print(f"\nDownloaded {len(downloaded_thumbnails)} thumbnails to {thumbnails_dir}/")

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get Azure Video Indexer credentials from environment variables
    account_id = os.environ.get("AZURE_VIDEO_INDEXER_ACCOUNT_ID")
    video_id = os.environ.get("AZURE_VIDEO_INDEXER_VIDEO_ID")
    access_token = os.environ.get("AZURE_VIDEO_INDEXER_ACCESS_TOKEN")
    
    print(f"Using account_id: {account_id}")
    print(f"Using video_id: {video_id}")
    
    if not all([account_id, video_id, access_token]):
        print("Error: Please set the following environment variables in .env file:")
        print("AZURE_VIDEO_INDEXER_ACCOUNT_ID")
        print("AZURE_VIDEO_INDEXER_VIDEO_ID")
        print("AZURE_VIDEO_INDEXER_ACCESS_TOKEN")
        return
    
    # Path to your metadata file
    metadata_file = "data/processed/LeNeil_20250401165517_cloud.json"
    
    if not os.path.exists(metadata_file):
        print(f"Error: Metadata file not found at {metadata_file}")
        return
    
    # Download thumbnails
    download_thumbnails(metadata_file, account_id, video_id, access_token)

if __name__ == "__main__":
    main() 