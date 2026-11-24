from flask import Flask, request, Response, jsonify, send_file
import yt_dlp, cv2, os, tempfile

app = Flask(__name__)

@app.route('/')
def home():
    return "esp32-yt-server & converter is live!"

@app.route('/search')
def search():
    q = request.args.get('q', 'cartoon')
    ydl_opts = {'quiet': True, 'extract_flat': True, 'default_search': 'ytsearch4'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(q, download=False)
        results = [{'id': e['id'], 'title': e['title'][:28]} for e in info.get('entries', [])]
    return jsonify(results)

def gen_frames(vid):
    url = f"https://www.youtube.com/watch?v={vid}"
    ydl_opts = {'format': 'best[height<=360][ext=mp4]/best', 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        stream_url = ydl.extract_info(url, download=False)['url']
    cap = cv2.VideoCapture(stream_url)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (320, 180))
        _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg.tobytes() + b'\r\n')
    cap.release()

@app.route('/stream')
def stream():
    vid = request.args.get('id', '')
    return Response(gen_frames(vid), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/convert', methods=['GET', 'POST'])
def convert_video():
    if request.method == 'GET':
        return '''
        <html><body style="font-family:sans-serif;text-align:center;padding:20px;background:#111;color:#fff;">
        <h2>ESP32 Video Recorder & Converter</h2>
        <button id="recBtn" onclick="startRec()" style="padding:12px 20px;font-size:18px;background:red;color:white;border:none;border-radius:8px;">Start Screen Rec</button>
        <button id="stopBtn" onclick="stopRec()" disabled style="padding:12px 20px;font-size:18px;background:orange;color:white;border:none;border-radius:8px;">Stop</button>
        <p id="timer" style="font-size:22px;color:#0f0;">0s</p>
        <hr><form method="POST" enctype="multipart/form-data">
        <p>Ya recorded/phone video chunein:</p>
        <input type="file" name="video" accept="video/*" required><br><br>
        <button type="submit" style="padding:12px 24px;font-size:18px;background:green;color:white;border:none;border-radius:8px;">Convert for ESP32 SD</button>
        </form>
        <script>
        let recorder, chunks=[], sec=0, tInt;
        async function startRec(){
          const stream = await navigator.mediaDevices.getDisplayMedia({video:true});
          recorder = new MediaRecorder(stream); chunks=[]; sec=0;
          recorder.ondataavailable = e => chunks.push(e.data);
          recorder.onstop = () => {
            clearInterval(tInt);
            const blob = new Blob(chunks, {type:'video/webm'});
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
            a.download = 'screen_rec.webm'; a.click();
          };
          recorder.start();
          document.getElementById('stopBtn').disabled = false;
          tInt = setInterval(()=>{ sec++; document.getElementById('timer').innerText = sec + 's'; }, 1000);
        }
        function stopRec(){ recorder.stop(); }
        </script></body></html>
        '''
    f = request.files['video']
    in_path = tempfile.mktemp(suffix='.mp4')
    out_path = tempfile.mktemp(suffix='.mjpeg')
    f.save(in_path)
    cap = cv2.VideoCapture(in_path)
    with open(out_path, 'wb') as out:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (320, 240))
            _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            out.write(jpg.tobytes())
    cap.release()
    os.remove(in_path)
    return send_file(out_path, as_attachment=True, download_name='esp32_video.mjpeg')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
