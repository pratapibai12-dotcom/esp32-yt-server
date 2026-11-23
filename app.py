from flask import Flask, request, Response, jsonify
import yt_dlp, cv2

app = Flask(__name__)

@app.route('/search')
def search():
    q = request.args.get('q', 'trending')
    ydl_opts = {'quiet': True, 'extract_flat': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch4:{q}", download=False)
        results = [{"id": e["id"], "title": e["title"][:28]} for e in info.get("entries", [])]
    return jsonify(results)

@app.route('/stream')
def stream():
    vid = request.args.get('id')
    ydl_opts = {'format': 'worst[ext=mp4]/worst', 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        url = info['url']
    def generate():
        cap = cv2.VideoCapture(url)
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            frame = cv2.resize(frame, (320, 180))
            _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 45])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg.tobytes() + b'\r\n')
        cap.release()
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
