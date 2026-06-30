import os
import cv2
import numpy as np
import sys

# Add backend dir to path to import app services
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.services.video_processor import interleave_videos

def create_mock_video(path, color, frame_count, width=320, height=180, fps=60):
    """
    Creates a mock video of solid color (BGR).
    """
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(path, fourcc, fps, (width, height))
    
    # Create solid frame
    # color: (B, G, R)
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = color
    
    for _ in range(frame_count):
        out.write(frame)
        
    out.release()
    print(f"Created mock video: {path} ({frame_count} frames, color={color})")

def verify_interleaved_video(path, expected_frames):
    """
    Verifies that the output video alternates colors every 6 frames:
    - Frames 0-5: Red (0, 0, 255)
    - Frames 6-11: Blue (255, 0, 0)
    - ...
    """
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError(f"Could not open output video for verification: {path}")
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"\nVerifying output video {path}:")
    print(f"Dimensions: {width}x{height}, FPS: {fps}, Total frames: {total_frames}")
    
    assert total_frames == expected_frames, f"Expected {expected_frames} frames, got {total_frames}"
    assert fps == 60.0, f"Expected 60.0 FPS, got {fps}"
    
    frame_idx = 0
    errors = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Get dominant color of frame (average across middle pixels)
        h, w = frame.shape[:2]
        center_color = frame[h//2, w//2] # BGR color
        
        # Every 12 frames has a pattern:
        # 0-5 (A) -> Red (BGR: [0, 0, 255])
        # 6-11 (B) -> Blue (BGR: [255, 0, 0])
        cycle_idx = frame_idx % 12
        is_red = cycle_idx < 6
        
        # BGR tolerances
        b, g, r = center_color
        
        if is_red:
            # Should be highly red: R > 200, B < 50, G < 50
            if r < 200 or b > 50 or g > 50:
                print(f"Error at frame {frame_idx}: Expected Red, got BGR {center_color}")
                errors += 1
        else:
            # Should be highly blue: B > 200, R < 50, G < 50
            if b < 200 or r > 50 or g > 50:
                print(f"Error at frame {frame_idx}: Expected Blue, got BGR {center_color}")
                errors += 1
                
        frame_idx += 1
        
    cap.release()
    
    if errors == 0:
        print("SUCCESS: Video alternating order and frames verified perfectly!")
        return True
    else:
        print(f"FAILED: Found {errors} verification errors.")
        return False

def run_tests():
    # Setup temporary directory for test assets
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp", "tests")
    os.makedirs(test_dir, exist_ok=True)
    
    video_a_path = os.path.join(test_dir, "test_video_a.mp4")
    video_b_path = os.path.join(test_dir, "test_video_b.mp4")
    output_path = os.path.join(test_dir, "test_interleaved_output.mp4")
    
    # 1. Create two mock videos
    # Video A: 60 frames, solid Red (BGR: 0, 0, 255)
    create_mock_video(video_a_path, color=(0, 0, 255), frame_count=60)
    
    # Video B: 120 frames, solid Blue (BGR: 255, 0, 0)
    create_mock_video(video_b_path, color=(255, 0, 0), frame_count=120)
    
    print("\nRunning interleave processing...")
    # 2. Interleave videos
    interleave_videos(
        video_a_path=video_a_path,
        video_b_path=video_b_path,
        output_path=output_path,
        progress_callback=lambda p: print(f"Progress: {p}%")
    )
    
    # 3. Verify output
    # Video A (shorter) is 60 frames. Video B is trimmed to 60 frames.
    # Combined output should be 60 + 60 = 120 frames.
    test_passed = verify_interleaved_video(output_path, expected_frames=120)
    
    # Clean up test files
    if os.path.exists(video_a_path):
        os.remove(video_a_path)
    if os.path.exists(video_b_path):
        os.remove(video_b_path)
    if os.path.exists(output_path):
        os.remove(output_path)
        
    if test_passed:
        print("\nAll unit tests passed.")
        sys.exit(0)
    else:
        print("\nUnit tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
