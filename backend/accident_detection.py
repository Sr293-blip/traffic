import time

previous_count = 0
static_frames = 0

def detect_accident(current_count):
    global previous_count, static_frames

    if current_count == previous_count:
        static_frames += 1
    else:
        static_frames = 0

    previous_count = current_count

    # If no movement for long time
    if static_frames > 150:
        return True
    return False