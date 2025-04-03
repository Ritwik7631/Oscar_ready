import os
from dotenv import load_dotenv
from VideoIndexerClient.Consts import Consts
from VideoIndexerClient.VideoIndexerClient import VideoIndexerClient
from pprint import pprint

def process_video(video_path):
    """Process a video using Azure Video Indexer and return the insights."""
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment variables
    config = {
        'AccountName': os.getenv('AccountName'),
        'ResourceGroup': os.getenv('ResourceGroup'),
        'SubscriptionId': os.getenv('SubscriptionId')
    }
    
    # Define API parameters
    ApiVersion = '2024-01-01'
    ApiEndpoint = 'https://api.videoindexer.ai'
    AzureResourceManager = 'https://management.azure.com'
    
    # Create and validate consts
    consts = Consts(
        ApiVersion, 
        ApiEndpoint, 
        AzureResourceManager, 
        config['AccountName'], 
        config['ResourceGroup'], 
        config['SubscriptionId']
    )
    
    # Create Video Indexer Client
    client = VideoIndexerClient()
    
    # Authenticate
    client.authenticate_async(consts)
    
    # Upload video from local file
    print(f"Uploading video: {video_path}")
    video_id = client.file_upload_async(video_path, video_name=None, excluded_ai=[])
    
    # Wait for indexing to complete
    print("Waiting for video indexing to complete...")
    client.wait_for_index_async(video_id)
    
    # Get video insights
    print("Getting video insights...")
    insights = client.get_video_async(video_id)
    
    # Save insights to JSON file
    output_dir = "data/processed"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(video_path))[0]}_cloud.json")
    
    with open(output_file, 'w') as f:
        import json
        json.dump(insights, f, indent=2)
    
    print(f"Insights saved to: {output_file}")
    return insights

def main():
    # Example usage
    video_path = "data/raw/LeNeil.mp4"  # Update this path to your video file
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        return
    
    insights = process_video(video_path)
    print("\nVideo processing completed successfully!")

if __name__ == "__main__":
    main() 