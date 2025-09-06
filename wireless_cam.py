import cv2
import time


def connect_to_wireless_camera(camera_url):
    """
    Simple function to connect to wireless webcam.
    """
    print(f"Connecting to wireless camera: {camera_url}")

    try:
        # Try to connect with OpenCV
        video_capture = cv2.VideoCapture(camera_url)

        # Set properties for better streaming
        video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        video_capture.set(cv2.CAP_PROP_FPS, 30)

        # Test if connection works
        ret, frame = video_capture.read()
        if ret and frame is not None:
            print("✓ Camera connected successfully!")
            return video_capture
        else:
            print("✗ Could not read frame from camera")
            video_capture.release()
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
