import cv2
import os
import numpy as np
import cvlib as cv
from cvlib.object_detection import draw_bbox
import progressbar

progressbar.ProgressBar.update = lambda self, value, **kwargs: None

PROCESSED_DIR = "data/processed"


def extract_keyframes(video_path, threshold=40):
    """
    Extract keyframes from the given video using frame differencing.

    Parameters:
        video_path (str): Path to the video file.
        threshold (float): The difference threshold to detect scene changes.

    Returns:
        list: A list of dictionaries containing keyframe info:
              {
                "frame_index": int,
                "keyframe_path": str,
                "diff_mean": float
              }
    """

    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR)

    cap = cv2.VideoCapture(video_path)

    keyframes = []

    prev_frame = None

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_frame is not None:
            diff = cv2.absdiff(gray, prev_frame)

            diff_mean = np.mean(diff)

            if diff_mean > threshold:
                keyframe_path = os.path.join(
                    PROCESSED_DIR, f"keyframe_{frame_idx}.jpg")
                cv2.imwrite(keyframe_path, frame)
                keyframes.append({
                    "frame_index": frame_idx,
                    "keyframe_path": keyframe_path,
                    "diff_mean": diff_mean
                })

        prev_frame = gray
        frame_idx += 1

    cap.release()
    return keyframes


def enhance_keyframe(keyframe):
    """
    Enhance a keyframe dictionary with object and face detection data.
    Uses cvlib for object detection (using yolov3-tiny) and face detection.
    Returns the updated keyframe dictionary.
    """
    image = cv2.imread(keyframe["keyframe_path"])
    if image is None:
        return keyframe

    # --- Object Detection ---
    # Detect common objects using cvlib with the YOLOv3-tiny model
    bbox, labels, confidences = cv.detect_common_objects(
        image, model='yolov3-tiny')
    objects = []
    for box, label, conf in zip(bbox, labels, confidences):
        objects.append({
            "label": label,
            "confidence": conf,
            "bounding_box": box
        })

    # --- Face Detection ---
    faces, face_confidences = cv.detect_face(image)
    detected_faces = []
    for face_box, face_conf in zip(faces, face_confidences):
        detected_faces.append({
            "bounding_box": face_box,
            "confidence": face_conf
        })

    keyframe["objects"] = objects
    keyframe["faces"] = detected_faces
    return keyframe


def process_video_metadata(video_path, threshold=40):
    """
    Extract keyframes from a video and enhance each keyframe with object and face detection data.
    Returns a list of enhanced keyframe dictionaries.
    """
    keyframes = extract_keyframes(video_path, threshold)
    enhanced_keyframes = [enhance_keyframe(kf) for kf in keyframes]
    return enhanced_keyframes
