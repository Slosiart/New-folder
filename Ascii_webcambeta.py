import cv2
import numpy as np
import tkinter as tk
from tkinter import Scale
import requests
from threading import Thread, Lock
import time

# API config
API_KEY = "e3184371b7a24e03be35e79f8f856012"
API_URL = f"https://newsapi.org/v2/top-headlines?category=technology&q=AI&language=en&apiKey={API_KEY}"

# ASCII config
COLUMNS = 120
ROWS = 40
CHARACTERS = " .:-=+*#%@"
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.4
THICKNESS = 1
CHAR_WIDTH = 8
CHAR_HEIGHT = 12
NEWS_ROWS = 2

# Buffers
buffer_height = ROWS * CHAR_HEIGHT
buffer_width = COLUMNS * CHAR_WIDTH
ascii_buffer = np.zeros((buffer_height, buffer_width, 3), dtype=np.uint8)

# Globals
news_lock = Lock()
current_news = "Loading AI news..."
scroll_pos = 0
base_brightness = 0.7
fade_factor = 0.8
feedback_intensity = 0.0
feedback_decay = 0.005
news_refresh_interval = 30  # seconds, will be adjustable

def fetch_real_news():
    try:
        response = requests.get(API_URL)
        data = response.json()
        headlines = [article["title"] for article in data.get("articles", [])]
        return " || ".join(headlines)
    except Exception as e:
        print(f"Error fetching news: {e}")
        return "Failed to fetch news."

def update_news_ticker():
    global current_news
    while True:
        with news_lock:
            current_news = fetch_real_news()
        time.sleep(news_refresh_interval)

def frame_to_ascii(frame, brightness):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (COLUMNS, ROWS - NEWS_ROWS))
    effective_brightness = brightness + feedback_intensity
    gray = cv2.convertScaleAbs(gray, alpha=effective_brightness, beta=0)
    
    ascii_image = np.zeros((buffer_height, buffer_width, 3), dtype=np.uint8)
    
    for row in range(ROWS - NEWS_ROWS):
        for col in range(COLUMNS):
            pixel_val = gray[row, col]
            char_idx = int(pixel_val / 255 * (len(CHARACTERS) - 1))
            ch = CHARACTERS[char_idx]
            x = col * CHAR_WIDTH
            y = (row + 1) * CHAR_HEIGHT
            cv2.putText(ascii_image, ch, (x, y), FONT, FONT_SCALE, (0, 255, 0), THICKNESS)
    
    return ascii_image

def add_news_ticker(buffer):
    global scroll_pos
    with news_lock:
        news_text = current_news
    text_width = len(news_text) * CHAR_WIDTH
    start_x = COLUMNS * CHAR_WIDTH - scroll_pos

    y_pos = (ROWS - NEWS_ROWS) * CHAR_HEIGHT + 10
    for i, ch in enumerate(news_text):
        x = start_x + i * CHAR_WIDTH
        if x < 0 or x >= buffer_width:
            continue
        cv2.putText(buffer, ch, (x, y_pos), FONT, FONT_SCALE, (50, 255, 50), THICKNESS)
        cv2.putText(buffer, ch, (x, y_pos + CHAR_HEIGHT), FONT, FONT_SCALE, (20, 200, 20), THICKNESS)

    scroll_pos = (scroll_pos + 2) % (text_width + buffer_width)

def video_loop():
    global ascii_buffer, feedback_intensity
    cap = cv2.VideoCapture(0)
    cv2.namedWindow("AI Vision Matrix", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("AI Vision Matrix", cv2.WND_PROP_FULLSCREEN, 1)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        new_ascii = frame_to_ascii(frame, base_brightness)
        ascii_buffer = cv2.addWeighted(ascii_buffer, fade_factor, new_ascii, (1 - fade_factor), 0)
        
        add_news_ticker(ascii_buffer)
        
        cv2.imshow("AI Vision Matrix", ascii_buffer)
        feedback_intensity = max(0, feedback_intensity - feedback_decay)
        
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

def control_window():
    global news_refresh_interval

    def on_slider_change(value):
        global news_refresh_interval
        news_refresh_interval = int(value)
        print(f"News refresh set to every {news_refresh_interval} seconds.")

    root = tk.Tk()
    root.title("News Refresh Controller")

    tk.Label(root, text="Adjust News Refresh Rate (seconds):").pack(pady=10)
    slider = Scale(root, from_=5, to=120, orient="horizontal", command=on_slider_change)
    slider.set(news_refresh_interval)
    slider.pack(padx=20, pady=20)

    root.mainloop()

if __name__ == "__main__":
    Thread(target=video_loop, daemon=True).start()
    Thread(target=update_news_ticker, daemon=True).start()
    control_window()
