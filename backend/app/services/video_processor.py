import cv2
import logging
import os

logger = logging.getLogger(__name__)

def interleave_videos(video_a_path: str, video_b_path: str, output_path: str, chunk_size: int = 6, progress_callback=None):
    """
    Reads Video A and Video B, trims them to the length of the shorter one,
    and interleaves them frame-by-frame in chunks of chunk_size frames.
    The final video is written at 60 FPS.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")

    if not os.path.exists(video_a_path):
        raise FileNotFoundError(f"Video A not found at: {video_a_path}")
    if not os.path.exists(video_b_path):
        raise FileNotFoundError(f"Video B not found at: {video_b_path}")

    # Open video readers
    cap_a = cv2.VideoCapture(video_a_path)
    cap_b = cv2.VideoCapture(video_b_path)

    if not cap_a.isOpened():
        raise ValueError(f"Could not open Video A: {video_a_path}")
    if not cap_b.isOpened():
        raise ValueError(f"Could not open Video B: {video_b_path}")

    try:
        # Get properties of input videos
        fps_a = cap_a.get(cv2.CAP_PROP_FPS)
        fps_b = cap_b.get(cv2.CAP_PROP_FPS)
        
        frames_a = int(cap_a.get(cv2.CAP_PROP_FRAME_COUNT))
        frames_b = int(cap_b.get(cv2.CAP_PROP_FRAME_COUNT))

        width_a = int(cap_a.get(cv2.CAP_PROP_FRAME_WIDTH))
        height_a = int(cap_a.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"Video A: {frames_a} frames, {fps_a} FPS, {width_a}x{height_a}")
        logger.info(f"Video B: {frames_b} frames, {fps_b} FPS")

        # Trim to the shorter video's frame count
        min_frames = min(frames_a, frames_b)
        logger.info(f"Processing target: {min_frames} frames from each video.")

        # Output video settings: 60 FPS as requested
        out_fps = 60.0
        
        # We use avc1 (H.264) codec for HTML5 browser compatibility.
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        
        # Ensure target directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Initialize VideoWriter
        out = cv2.VideoWriter(output_path, fourcc, out_fps, (width_a, height_a))
        
        if not out.isOpened():
            raise RuntimeError("Could not open VideoWriter. Codec or file path issue.")

        processed_frames = 0

        # Read sequentially without seeking (extremely fast and frame-perfect)
        while processed_frames < min_frames:
            current_chunk_size = min(chunk_size, min_frames - processed_frames)
            if current_chunk_size <= 0:
                break

            # Read and write 6 frames from Video A
            for _ in range(current_chunk_size):
                ret, frame = cap_a.read()
                if not ret:
                    break
                out.write(frame)

            # Read and write 6 frames from Video B
            for _ in range(current_chunk_size):
                ret, frame = cap_b.read()
                if not ret:
                    break
                
                # Resize B's frame to A's dimensions to prevent video stream errors
                h_b, w_b = frame.shape[:2]
                if w_b != width_a or h_b != height_a:
                    frame = cv2.resize(frame, (width_a, height_a), interpolation=cv2.INTER_AREA)
                
                out.write(frame)

            processed_frames += current_chunk_size
            
            if progress_callback:
                progress = min(100, int((processed_frames / min_frames) * 100))
                progress_callback(progress)

        logger.info(f"Video processing finished. Wrote {processed_frames * 2} frames to {output_path}")

    finally:
        cap_a.release()
        cap_b.release()
        if 'out' in locals():
            out.release()
