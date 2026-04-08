import cv2
from urllib.parse import urlparse, urlunparse


def build_camera_url_candidates(raw_url):
    """Generate likely stream URLs for common IP camera apps."""
    raw_url = raw_url.strip()
    if not raw_url:
        return []

    if "://" not in raw_url:
        raw_url = f"http://{raw_url}"

    parsed = urlparse(raw_url)
    normalized = parsed._replace(params="", fragment="")

    candidates = [urlunparse(normalized)]

    if normalized.path.strip("/") == "":
        base = urlunparse(normalized._replace(path="", query="")).rstrip("/")
        candidates.extend(
            [
                f"{base}/video",
                f"{base}/mjpeg",
                f"{base}/stream",
                f"{base}/?action=stream",
                f"{base}/shot.jpg",
            ]
        )

    unique_candidates = []
    seen = set()
    for candidate in candidates:
        if candidate not in seen:
            unique_candidates.append(candidate)
            seen.add(candidate)

    return unique_candidates


def try_open_capture(source, max_reads=25):
    """Open a source and verify at least one frame can be read."""
    video_capture = cv2.VideoCapture(source)
    if not video_capture.isOpened():
        video_capture.release()
        return None

    video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    video_capture.set(cv2.CAP_PROP_FPS, 30)

    for _ in range(max_reads):
        ret, frame = video_capture.read()
        if ret and frame is not None:
            return video_capture

    video_capture.release()
    return None


def connect_to_wireless_camera(camera_url):
    """
    Simple function to connect to wireless webcam.
    """
    print(f"Connecting to wireless camera: {camera_url}")

    try:
        for candidate_url in build_camera_url_candidates(camera_url):
            print(f"Trying: {candidate_url}")
            video_capture = try_open_capture(candidate_url)
            if video_capture is not None:
                print(f"✓ Camera connected successfully! ({candidate_url})")
                return video_capture

        print("✗ Could not read frame from camera")
        print("Tip: for Android IP Webcam, use: http://<phone-ip>:8080/video")
        return None

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return None


def main():
    # Get camera URL from user
    camera_url = input("Enter your wireless camera URL: ")

    # Connect to camera
    video_capture = connect_to_wireless_camera(camera_url)

    if not video_capture:
        print("Failed to connect to camera. Exiting...")
        return

    print("Camera connected! Press 'q' to quit.")

    # Main video loop
    while True:
        ret, frame = video_capture.read()

        if not ret:
            print("Failed to read frame")
            break

        # Display the frame
        cv2.imshow("Wireless Webcam", frame)

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # Clean up
    video_capture.release()
    cv2.destroyAllWindows()
    print("Camera disconnected.")


if __name__ == "__main__":
    main()
