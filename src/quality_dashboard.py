import streamlit as st
import json
import pandas as pd
import os
from datetime import datetime

def load_annotations(base_name):
    """Load annotations from the separate annotations file."""
    annotations_file = os.path.join("data", "processed", f"{base_name}_annotations.json")
    if os.path.exists(annotations_file):
        try:
            with open(annotations_file, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def display_quality_metrics(metadata_file):
    """
    Load metadata and annotations from their respective files and display key quality metrics.
    Metrics include total keyframes, number of annotated keyframes, annotation completeness percentage,
    and insights from Azure Video Indexer.
    """
    try:
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
            
        # Get base video name
        video_name = metadata.get("name", "")
        base_name = video_name.split('_')[0]
        
        # Load annotations
        annotations = load_annotations(base_name)
        
        # Get video insights
        video_insights = metadata.get("videos", [{}])[0].get("insights", {})
        
        # Calculate basic metrics
        total_keyframes = len([shot for shot in video_insights.get("shots", [])])
        annotated_frames = len(annotations)
        completeness = (annotated_frames / total_keyframes * 100) if total_keyframes > 0 else 0
        
        # Calculate Azure insights metrics
        total_labels = len(video_insights.get("labels", []))
        total_ocr = len(video_insights.get("ocr", []))
        
        # Display metrics
        st.subheader("Quality Metrics")
        
        # Basic metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Keyframes", total_keyframes)
            st.metric("Annotated Frames", annotated_frames)
            st.metric("Annotation Completeness", f"{completeness:.1f}%")
        
        with col2:
            st.metric("Detected Labels", total_labels)
            st.metric("OCR Text Segments", total_ocr)
        
        # Detailed insights
        st.subheader("Detailed Insights")
        
        # Labels breakdown
        if video_insights.get("labels"):
            st.write("**Top Labels:**")
            labels_df = pd.DataFrame([
                {
                    "Label": label.get("name"),
                    "Instances": len(label.get("instances", []))
                }
                for label in video_insights.get("labels", [])
            ]).sort_values("Instances", ascending=False).head(10)
            st.dataframe(labels_df, use_container_width=True)
        
        # OCR text
        if video_insights.get("ocr"):
            st.write("**Detected Text:**")
            ocr_df = pd.DataFrame([
                {
                    "Text": ocr.get("text"),
                    "Instances": len(ocr.get("instances", []))
                }
                for ocr in video_insights.get("ocr", [])
            ])
            st.dataframe(ocr_df, use_container_width=True)

        # Add export annotations button
        if annotations:
            st.subheader("Annotation Summary")
            annotations_df = pd.DataFrame([
                {"Frame ID": frame_id, "Annotation": annotation}
                for frame_id, annotation in annotations.items()
            ])
            st.dataframe(annotations_df, use_container_width=True)
            
            # Create a download button for annotations
            csv = annotations_df.to_csv(index=False)
            st.download_button(
                label="Export Annotations",
                data=csv,
                file_name=f"{base_name}_annotations.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error loading data: {e}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return

def export_metrics(metadata_file):
    """
    Create a comprehensive DataFrame of the keyframes and annotations,
    and provide a download button for users to export the metrics.
    """
    try:
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        # Get base video name
        video_name = metadata.get("name", "")
        base_name = video_name.split('_')[0]
        
        # Load annotations
        annotations = load_annotations(base_name)
        
        # Get video insights
        video_insights = metadata.get("videos", [{}])[0].get("insights", {})
        
        # Prepare data for export
        data = []
        for shot in video_insights.get("shots", []):
            for keyframe in shot.get("keyFrames", []):
                frame_id = keyframe.get("id")
                
                # Get all labels that appear in this keyframe
                frame_labels = []
                for label in video_insights.get("labels", []):
                    for instance in label.get("instances", []):
                        if any(kf.get("id") == frame_id for kf in instance.get("keyFrames", [])):
                            frame_labels.append(label.get('name'))
                
                # Get OCR text that appears in this keyframe
                frame_ocr = []
                for ocr in video_insights.get("ocr", []):
                    for instance in ocr.get("instances", []):
                        if any(kf.get("id") == frame_id for kf in instance.get("keyFrames", [])):
                            frame_ocr.append(ocr.get('text'))
                
                data.append({
                    "Frame ID": frame_id,
                    "Annotation": annotations.get(str(frame_id), ""),
                    "Shot Tags": ", ".join(shot.get("tags", [])),
                    "Labels": ", ".join(frame_labels),
                    "OCR Text": ", ".join(frame_ocr)
                })
        
        # Create DataFrame and export button
        df = pd.DataFrame(data)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Export Quality Metrics",
            data=csv,
            file_name=f"{base_name}_quality_metrics.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error exporting metrics: {e}")
        return
