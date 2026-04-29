import os
import uuid
import json
import logging

from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

from video_editor import create_comparison_video, create_summary_video

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB limit

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'outputs')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_obj):
    ext = secure_filename(file_obj.filename).rsplit('.', 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file_obj.save(save_path)
    return save_path


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/comparison', methods=['POST'])
def api_comparison():
    before = request.files.get('before_video')
    after = request.files.get('after_video')

    if not before or not after:
        return jsonify({'status': 'error', 'message': '두 영상 파일을 모두 업로드해 주세요.'}), 400

    if not allowed_file(before.filename) or not allowed_file(after.filename):
        return jsonify({'status': 'error', 'message': '지원하지 않는 파일 형식입니다.'}), 400

    before_path = save_upload(before)
    after_path = save_upload(after)

    output_filename = f"comparison_{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    try:
        create_comparison_video(before_path, after_path, output_path)
        return jsonify({'status': 'success', 'filename': output_filename})
    except Exception as e:
        logger.exception('comparison video processing failed')
        return jsonify({'status': 'error', 'message': '영상 처리 중 오류가 발생했습니다.'}), 500
    finally:
        for p in (before_path, after_path):
            try:
                os.remove(p)
            except OSError:
                pass


@app.route('/api/summary', methods=['POST'])
def api_summary():
    lesson = request.files.get('lesson_video')
    clips_raw = request.form.get('clips', '[]')

    if not lesson:
        return jsonify({'status': 'error', 'message': '레슨 영상을 업로드해 주세요.'}), 400

    if not allowed_file(lesson.filename):
        return jsonify({'status': 'error', 'message': '지원하지 않는 파일 형식입니다.'}), 400

    try:
        clips = json.loads(clips_raw)
    except (json.JSONDecodeError, ValueError):
        return jsonify({'status': 'error', 'message': '클립 데이터 형식이 올바르지 않습니다.'}), 400

    if not clips:
        return jsonify({'status': 'error', 'message': '최소 한 개의 클립을 추가해 주세요.'}), 400

    lesson_path = save_upload(lesson)

    output_filename = f"summary_{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    try:
        create_summary_video(lesson_path, clips, output_path)
        return jsonify({'status': 'success', 'filename': output_filename})
    except ValueError:
        logger.warning('summary clip validation error', exc_info=True)
        return jsonify({'status': 'error', 'message': '클립 시간 값이 올바르지 않습니다. 시작/종료 시간을 확인해 주세요.'}), 400
    except Exception:
        logger.exception('summary video processing failed')
        return jsonify({'status': 'error', 'message': '영상 처리 중 오류가 발생했습니다.'}), 500
    finally:
        try:
            os.remove(lesson_path)
        except OSError:
            pass


@app.route('/api/video-info', methods=['POST'])
def api_video_info():
    video = request.files.get('video')
    if not video:
        return jsonify({'status': 'error', 'message': '영상 파일을 업로드해 주세요.'}), 400

    if not allowed_file(video.filename):
        return jsonify({'status': 'error', 'message': '지원하지 않는 파일 형식입니다.'}), 400

    video_path = save_upload(video)
    try:
        from moviepy.editor import VideoFileClip
        with VideoFileClip(video_path) as clip:
            info = {
                'duration': clip.duration,
                'fps': clip.fps,
                'size': list(clip.size),
            }
        return jsonify(info)
    except Exception as e:
        logger.exception('video-info extraction failed')
        return jsonify({'status': 'error', 'message': '영상 정보를 읽을 수 없습니다.'}), 500
    finally:
        try:
            os.remove(video_path)
        except OSError:
            pass


@app.route('/download/<filename>')
def download(filename):
    safe = secure_filename(filename)
    return send_from_directory(OUTPUT_FOLDER, safe, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
