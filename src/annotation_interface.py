import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
import cv2
import numpy as np
from src.metadata_extraction import extract_keyframes as extract_keyframes_opencv

def parse_time(time_str):
    """Parse time string in format 'HH:MM:SS.mmm' to seconds."""
    try:
        h, m, s = time_str.split(':')
        s, ms = s.split('.')
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    except:
        return 0

def format_timing(start_time, end_time):
    """Format timing information in a readable way."""
    if not start_time or not end_time:
        return "Timing not available"
    try:
        start = parse_time(start_time)
        end = parse_time(end_time)
        duration = end - start
        return f"{start_time} - {end_time} ({duration:.1f}s)"
    except:
        return "Invalid timing format"

def extract_keyframes(metadata):
    """Extract keyframes from video using Azure Video Indexer timing information."""
    # Get video name from metadata
    video_name = metadata.get("name")
    if not video_name:
        raise ValueError("Video name not found in metadata")
    
    # Extract base video name (remove timestamp) and sanitize it
    base_name = video_name.split('_')[0]
    # Replace special characters with underscores
    sanitized_name = "".join(c if c.isalnum() else "_" for c in base_name)
    
    # Look for video file in raw_videos directory
    raw_videos_dir = os.path.join("data", "raw_videos")
    if not os.path.exists(raw_videos_dir):
        raise ValueError(f"Raw videos directory not found: {raw_videos_dir}")
    
    # Find the video file that matches the base name
    video_files = [f for f in os.listdir(raw_videos_dir) if f.startswith(base_name) and f.endswith(('.mp4', '.mov', '.avi', '.mkv'))]
    if not video_files:
        raise ValueError(f"No video file found in {raw_videos_dir} that matches the base name: {base_name}")
    
    # Use the first matching video file
    video_path = os.path.join(raw_videos_dir, video_files[0])
    
    # Get video insights from Azure metadata
    video_insights = metadata.get("videos", [{}])[0].get("insights", {})
    
    # Create thumbnails directory if it doesn't exist
    thumbnails_dir = os.path.join("thumbnails", sanitized_name)
    os.makedirs(thumbnails_dir, exist_ok=True)
    
    # Collect all significant timestamps from Azure insights
    timestamps = set()
    
    # Add timestamps from labels
    for label in video_insights.get("labels", []):
        for instance in label.get("appearances", []):
            timestamps.add(parse_time(instance.get("startTime")))
            timestamps.add(parse_time(instance.get("endTime")))
    
    # Add timestamps from transcript
    for segment in video_insights.get("transcript", []):
        for instance in segment.get("instances", []):
            timestamps.add(parse_time(instance.get("adjustedStart")))
            timestamps.add(parse_time(instance.get("adjustedEnd")))
    
    # Add timestamps from shots (if available)
    for shot in video_insights.get("shots", []):
        timestamps.add(parse_time(shot.get("start")))
        timestamps.add(parse_time(shot.get("end")))
    
    # Sort timestamps
    timestamps = sorted(list(timestamps))
    
    # Open video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    formatted_keyframes = []
    
    # Extract frame at each significant timestamp
    for frame_index, timestamp in enumerate(timestamps):
        # Convert timestamp to frame number
        frame_number = int(timestamp * fps)
        
        # Set frame position
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if ret:
            # Save frame as thumbnail with absolute path
            thumbnail_path = os.path.abspath(os.path.join(thumbnails_dir, f"frame_{frame_index}.jpg"))
            cv2.imwrite(thumbnail_path, frame)
            
            # Format time string
            hours = int(timestamp // 3600)
            minutes = int((timestamp % 3600) // 60)
            seconds = int(timestamp % 60)
            milliseconds = int((timestamp * 1000) % 1000)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            
            # Create keyframe data
            keyframe_data = {
                "frame_index": frame_index,
                "keyframe_path": thumbnail_path,
                "start_time": time_str,
                "end_time": time_str,
                "shot_tags": [],
                "labels": [],
                "faces": [],
                "ocr_text": []
            }
            
            # Add labels that are active at this timestamp
            for label in video_insights.get("labels", []):
                for instance in label.get("appearances", []):
                    if (parse_time(instance.get("startTime", "0:00:00")) <= timestamp and
                        parse_time(instance.get("endTime", "0:00:00")) >= timestamp):
                        keyframe_data["labels"].append({
                            "name": label.get("name"),
                            "confidence": instance.get("confidence", 0)
                        })
            
            # Add faces that are visible at this timestamp
            for face in video_insights.get("faces", []):
                for instance in face.get("instances", []):
                    if (parse_time(instance.get("start", "0:00:00")) <= timestamp and
                        parse_time(instance.get("end", "0:00:00")) >= timestamp):
                        keyframe_data["faces"].append({
                            "name": face.get("name"),
                            "confidence": instance.get("confidence", 0)
                        })
            
            # Add OCR text visible at this timestamp
            for ocr in video_insights.get("ocr", []):
                for instance in ocr.get("instances", []):
                    if (parse_time(instance.get("start", "0:00:00")) <= timestamp and
                        parse_time(instance.get("end", "0:00:00")) >= timestamp):
                        keyframe_data["ocr_text"].append({
                            "text": ocr.get("text"),
                            "confidence": ocr.get("confidence", 0)
                        })
            
            # Add shot tags from the current shot
            for shot in video_insights.get("shots", []):
                if (parse_time(shot.get("start", "0:00:00")) <= timestamp and
                    parse_time(shot.get("end", "0:00:00")) >= timestamp):
                    keyframe_data["shot_tags"].extend(shot.get("tags", []))
            
            formatted_keyframes.append(keyframe_data)
    
    cap.release()
    return formatted_keyframes

def get_latest_metadata_file(base_name):
    """Get the most recent metadata file for a given video."""
    processed_dir = os.path.join("data", "processed")
    metadata_files = [f for f in os.listdir(processed_dir) 
                     if f.startswith(base_name) and f.endswith("_cloud.json")]
    if not metadata_files:
        return None
    
    # Sort by creation time, newest first
    metadata_files.sort(key=lambda x: os.path.getctime(os.path.join(processed_dir, x)), reverse=True)
    return os.path.join(processed_dir, metadata_files[0])

def format_insights_for_display(metadata):
    """Format video insights into a more readable structure."""
    insights = metadata.get("videos", [{}])[0].get("insights", {})
    
    formatted_insights = {
        "Basic Information": {
            "Video Name": metadata.get("name", "Unknown"),
            "Duration": insights.get("duration", "Unknown"),
            "Language": insights.get("language", "Unknown"),
            "Source Languages": ", ".join(insights.get("sourceLanguages", [])),
        },
        "Transcript": [
            {
                "Text": segment.get("text", ""),
                "Speaker": f"Speaker {segment.get('speakerId', 'Unknown')}",
                "Confidence": f"{segment.get('confidence', 0) * 100:.1f}%",
                "Timing": f"{segment.get('instances', [{}])[0].get('adjustedStart', '')} - {segment.get('instances', [{}])[0].get('adjustedEnd', '')}"
            }
            for segment in insights.get("transcript", [])
        ],
        "Labels": [
            {
                "Name": label.get("name", ""),
                "Confidence": f"{instance.get('confidence', 0) * 100:.1f}%",
                "Timing": f"{instance.get('startTime', '')} - {instance.get('endTime', '')}"
            }
            for label in insights.get("labels", [])
            for instance in label.get("appearances", [])
        ],
        "Faces": [
            {
                "Name": face.get("name", "Unknown"),
                "Confidence": f"{instance.get('confidence', 0) * 100:.1f}%",
                "Timing": f"{instance.get('start', '')} - {instance.get('end', '')}"
            }
            for face in insights.get("faces", [])
            for instance in face.get("instances", [])
        ],
        "OCR Text": [
            {
                "Text": ocr.get("text", ""),
                "Confidence": f"{ocr.get('confidence', 0) * 100:.1f}%",
                "Timing": f"{instance.get('start', '')} - {instance.get('end', '')}"
            }
            for ocr in insights.get("ocr", [])
            for instance in ocr.get("instances", [])
        ],
        "Sentiments": [
            {
                "Sentiment": sentiment.get("sentimentKey", ""),
                "Duration Ratio": f"{sentiment.get('seenDurationRatio', 0) * 100:.1f}%",
                "Timing": f"{instance.get('startTime', '')} - {instance.get('endTime', '')}"
            }
            for sentiment in insights.get("sentiments", [])
            for instance in sentiment.get("appearances", [])
        ],
        "Emotions": [
            {
                "Emotion": emotion.get("type", ""),
                "Duration Ratio": f"{emotion.get('seenDurationRatio', 0) * 100:.1f}%",
                "Timing": f"{instance.get('startTime', '')} - {instance.get('endTime', '')}"
            }
            for emotion in insights.get("emotions", [])
            for instance in emotion.get("appearances", [])
        ],
        "Audio Effects": [
            {
                "Effect": effect.get("audioEffectKey", ""),
                "Duration Ratio": f"{effect.get('seenDurationRatio', 0) * 100:.1f}%",
                "Timing": f"{instance.get('startTime', '')} - {instance.get('endTime', '')}"
            }
            for effect in insights.get("audioEffects", [])
            for instance in effect.get("appearances", [])
        ],
        "Topics": [
            {
                "Topic": topic.get("name", ""),
                "Confidence": f"{topic.get('confidence', 0) * 100:.1f}%",
                "Timing": f"{instance.get('startTime', '')} - {instance.get('endTime', '')}"
            }
            for topic in insights.get("topics", [])
            for instance in topic.get("appearances", [])
        ],
        "Brands": [
            {
                "Brand": brand.get("name", ""),
                "Confidence": f"{brand.get('confidence', 0) * 100:.1f}%",
                "Description": brand.get("description", ""),
                "Timing": f"{instance.get('startTime', '')} - {instance.get('endTime', '')}"
            }
            for brand in insights.get("brands", [])
            for instance in brand.get("appearances", [])
        ],
        "Named People": [
            {
                "Name": person.get("name", ""),
                "Confidence": f"{person.get('confidence', 0) * 100:.1f}%",
                "Description": person.get("description", ""),
                "Timing": f"{instance.get('startTime', '')} - {instance.get('endTime', '')}"
            }
            for person in insights.get("namedPeople", [])
            for instance in person.get("appearances", [])
        ],
        "Named Locations": [
            {
                "Location": location.get("name", ""),
                "Confidence": f"{location.get('confidence', 0) * 100:.1f}%",
                "Description": location.get("description", ""),
                "Timing": f"{instance.get('startTime', '')} - {instance.get('endTime', '')}"
            }
            for location in insights.get("namedLocations", [])
            for instance in location.get("appearances", [])
        ]
    }
    
    return formatted_insights

def annotation_interface(metadata_file):
    """
    Displays keyframes with their metadata and allows users to add or edit annotations.
    Saves the updated annotations back to a separate annotations file.
    """
    # Initialize session state for tracking changes
    if "has_unsaved_changes" not in st.session_state:
        st.session_state.has_unsaved_changes = False
    if "annotations" not in st.session_state:
        st.session_state.annotations = {}

    try:
        # Ensure processed directory exists
        processed_dir = os.path.join("data", "processed")
        os.makedirs(processed_dir, exist_ok=True)

        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        keyframes = extract_keyframes(metadata)
        
        # Get base video name for consistent annotations file path
        video_name = metadata.get("name", "")
        base_name = video_name.split('_')[0]  # Get base name without timestamp
        
        # Get the most recent metadata file
        latest_metadata = get_latest_metadata_file(base_name)
        if latest_metadata and latest_metadata != metadata_file:
            st.info(f"Using the most recent metadata file: {os.path.basename(latest_metadata)}")
        
        # Load existing annotations from annotations file
        annotations_file = os.path.join(processed_dir, f"{base_name}_annotations.json")
        saved_annotations = {}
        if os.path.exists(annotations_file):
            try:
                with open(annotations_file, "r") as f:
                    saved_annotations = json.load(f)
                st.success(f"Loaded existing annotations from {annotations_file}")
            except json.JSONDecodeError:
                st.warning("Annotations file was corrupted. Starting fresh.")
                saved_annotations = {}
            except Exception as e:
                st.warning(f"Could not load annotations: {str(e)}")
                saved_annotations = {}
        
        # Load annotations into keyframes and session state
        for frame_idx, annotation in saved_annotations.items():
            for kf in keyframes:
                if str(kf["frame_index"]) == str(frame_idx):
                    kf["annotation"] = annotation
                    st.session_state[f"annot_{kf['frame_index']}"] = annotation
                    break

    except Exception as e:
        st.error(f"Error loading metadata file: {e}")
        return

    st.title("Video Keyframe Annotations")
    
    # Main content area
    if not keyframes:
        st.info("No keyframes available for annotation.")
        return

    # Display video insights in an expandable section
    with st.expander("Video Insights", expanded=True):
        # Add download buttons for insights and metadata
        col1, col2 = st.columns(2)
        with col1:
            formatted_insights = format_insights_for_display(metadata)
            insights_json = json.dumps(formatted_insights, indent=2)
            st.download_button(
                label="Download Formatted Insights",
                data=insights_json,
                file_name=f"{base_name}_formatted_insights.json",
                mime="application/json"
            )
        with col2:
            st.download_button(
                label="Download Raw Metadata",
                data=json.dumps(metadata, indent=2),
                file_name=f"{base_name}_raw_metadata.json",
                mime="application/json"
            )
        
        # Display basic information
        st.subheader("Basic Information")
        for key, value in formatted_insights["Basic Information"].items():
            st.text(f"{key}: {value}")
        
        # Display transcript
        st.subheader("Transcript")
        for segment in formatted_insights["Transcript"]:
            st.text(f"[{segment['Timing']}] {segment['Speaker']} ({segment['Confidence']}): {segment['Text']}")
        
        # Display labels
        st.subheader("Labels")
        for label in formatted_insights["Labels"]:
            st.text(f"[{label['Timing']}] {label['Name']} ({label['Confidence']})")
        
        # Display faces
        st.subheader("Faces")
        for face in formatted_insights["Faces"]:
            st.text(f"[{face['Timing']}] {face['Name']} ({face['Confidence']})")
        
        # Display OCR text
        st.subheader("OCR Text")
        for ocr in formatted_insights["OCR Text"]:
            st.text(f"[{ocr['Timing']}] {ocr['Text']} ({ocr['Confidence']})")
        
        # Display sentiments
        st.subheader("Sentiments")
        for sentiment in formatted_insights["Sentiments"]:
            st.text(f"[{sentiment['Timing']}] {sentiment['Sentiment']} ({sentiment['Duration Ratio']})")
        
        # Display emotions
        st.subheader("Emotions")
        for emotion in formatted_insights["Emotions"]:
            st.text(f"[{emotion['Timing']}] {emotion['Emotion']} ({emotion['Duration Ratio']})")
        
        # Display audio effects
        st.subheader("Audio Effects")
        for effect in formatted_insights["Audio Effects"]:
            st.text(f"[{effect['Timing']}] {effect['Effect']} ({effect['Duration Ratio']})")
        
        # Display topics
        st.subheader("Topics")
        for topic in formatted_insights["Topics"]:
            st.text(f"[{topic['Timing']}] {topic['Topic']} ({topic['Confidence']})")
        
        # Display brands
        st.subheader("Brands")
        for brand in formatted_insights["Brands"]:
            st.text(f"[{brand['Timing']}] {brand['Brand']} ({brand['Confidence']})")
            if brand["Description"]:
                st.text(f"Description: {brand['Description']}")
        
        # Display named people
        st.subheader("Named People")
        for person in formatted_insights["Named People"]:
            st.text(f"[{person['Timing']}] {person['Name']} ({person['Confidence']})")
            if person["Description"]:
                st.text(f"Description: {person['Description']}")
        
        # Display named locations
        st.subheader("Named Locations")
        for location in formatted_insights["Named Locations"]:
            st.text(f"[{location['Timing']}] {location['Location']} ({location['Confidence']})")
            if location["Description"]:
                st.text(f"Description: {location['Description']}")

    # Display keyframes in a grid
    st.header("Keyframes")
    if st.session_state.has_unsaved_changes:
        st.warning("You have unsaved changes!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Annotations", type="primary"):
            try:
                # Create annotations dictionary from session state
                annotations = {}
                text_area_keys = [k for k in st.session_state.keys() if k.startswith("annot_")]
                
                for key in text_area_keys:
                    frame_idx = key.split("_")[1]
                    annotation = st.session_state[key]
                    if annotation and annotation.strip():
                        annotations[frame_idx] = annotation
                
                annotations_file = os.path.join(processed_dir, f"{base_name}_annotations.json")
                
                with open(annotations_file, "w") as f:
                    json.dump(annotations, f, indent=4)
                
                st.session_state.has_unsaved_changes = False
                st.success(f"Annotations saved successfully to {annotations_file}!")
                
            except Exception as e:
                st.error(f"Failed to save annotations: {e}")
    
    with col2:
        if st.button("Export Annotations"):
            try:
                annotations_data = []
                for keyframe in keyframes:
                    annotations_data.append({
                        "Frame Index": keyframe.get("frame_index"),
                        "Annotation": keyframe.get("annotation", ""),
                        "Start Time": keyframe.get("start_time"),
                        "End Time": keyframe.get("end_time"),
                        "Labels": ", ".join([l["name"] for l in keyframe.get("labels", [])]),
                        "Faces": ", ".join([f["name"] for f in keyframe.get("faces", [])]),
                        "OCR Text": " ".join([t["text"] for t in keyframe.get("ocr_text", [])])
                    })
                df = pd.DataFrame(annotations_data)
                
                export_path = os.path.join("data", "processed", f"{base_name}_annotations.csv")
                df.to_csv(export_path, index=False)
                st.success(f"Annotations exported to {export_path}")
            except Exception as e:
                st.error(f"Failed to export annotations: {e}")

    num_columns = 3
    for i in range(0, len(keyframes), num_columns):
        cols = st.columns(num_columns)
        for j, col in enumerate(cols):
            index = i + j
            if index < len(keyframes):
                keyframe = keyframes[index]
                with col:
                    st.subheader(f"Frame {keyframe.get('frame_index', index)}")
                    
                    # Display keyframe image
                    if keyframe.get("keyframe_path"):
                        if os.path.exists(keyframe["keyframe_path"]):
                            st.image(keyframe["keyframe_path"], use_container_width=True)
                        else:
                            st.error(f"Image not found: {keyframe['keyframe_path']}")
                    else:
                        st.warning("No image available.")
                    
                    # Display timing information
                    timing = format_timing(
                        keyframe.get("start_time"),
                        keyframe.get("end_time")
                    )
                    st.caption(timing)
                    
                    # Display detected labels
                    if keyframe.get("labels"):
                        st.caption("Labels: " + ", ".join([l["name"] for l in keyframe["labels"]]))
                    
                    # Display detected faces
                    if keyframe.get("faces"):
                        st.caption("Faces: " + ", ".join([f["name"] for f in keyframe["faces"]]))
                    
                    # Display OCR text
                    if keyframe.get("ocr_text"):
                        st.caption("OCR: " + " ".join([t["text"] for t in keyframe["ocr_text"]]))
                    
                    # Display shot tags
                    if keyframe.get("shot_tags"):
                        st.caption("Shot Tags: " + ", ".join(keyframe["shot_tags"]))
                    
                    # Annotation input
                    current_annotation = keyframe.get("annotation", "")
                    key = f"annot_{keyframe['frame_index']}"
                    annotation = st.text_area(
                        "Annotation",
                        value=current_annotation,
                        key=key,
                        height=100,
                        on_change=lambda: st.session_state.__setitem__('has_unsaved_changes', True)
                    )
                    
                    # Update keyframe with current annotation from session state
                    if key in st.session_state:
                        keyframe["annotation"] = st.session_state[key]
                        if st.session_state[key] != current_annotation:
                            st.info(f"Updated annotation for frame {keyframe['frame_index']}: {st.session_state[key]}")

    # Display summary of annotations
    st.header("Annotation Summary")
    annotations_df = pd.DataFrame([
        {
            "Frame": kf.get("frame_index"),
            "Annotation": kf.get("annotation", ""),
            "Timing": format_timing(kf.get("start_time"), kf.get("end_time")),
            "Labels": ", ".join([l["name"] for l in kf.get("labels", [])]),
            "Faces": ", ".join([f["name"] for f in kf.get("faces", [])]),
            "OCR Text": " ".join([t["text"] for t in kf.get("ocr_text", [])])
        }
        for kf in keyframes
    ])
    st.dataframe(annotations_df, use_container_width=True)
