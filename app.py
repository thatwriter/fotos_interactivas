from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import time
import subprocess
import re
import threading
import atexit

# Intentar importar qrcode (si no está instalado, el QR se deshabilita)
try:
    import qrcode
    import qrcode.image.svg
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("⚠️  Librería 'qrcode' no instalada. QR deshabilitado.")

app = Flask(__name__)

# Configuración
UPLOAD_FOLDER = 'static/videos'
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi', 'mkv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Variable global para la URL del túnel
TUNNEL_URL = None
QR_TIMESTAMP = None
cloudflared_process = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================================
# TÚNEL Y QR AUTOMÁTICO
# ==========================================
def start_cloudflared():
    """Inicia cloudflared como proceso hijo y captura la URL"""
    global TUNNEL_URL, cloudflared_process
    
    # Verificar que cloudflared esté instalado
    try:
        subprocess.run(['cloudflared', '--version'], 
                      capture_output=True, check=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️  cloudflared no disponible. Servidor solo en modo local.")
        return
    
    print("🌐 Iniciando túnel público con cloudflared...")
    
    try:
        # Iniciar cloudflared como subprocess
        cloudflared_process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', 'http://localhost:5000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Registrar cleanup al cerrar
        atexit.register(stop_cloudflared)
        
        # Leer la salida en un hilo separado para no bloquear
        def read_output():
            global TUNNEL_URL
            url_pattern = re.compile(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com')
            
            for line in cloudflared_process.stdout:
                match = url_pattern.search(line)
                if match and TUNNEL_URL is None:
                    TUNNEL_URL = match.group(0)
                    print(f"\n✅ ¡TÚNEL PÚBLICO ACTIVO!")
                    print(f"🔗 URL: {TUNNEL_URL}")
                    generate_qr(TUNNEL_URL)
        
        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()
        
    except Exception as e:
        print(f"❌ Error iniciando cloudflared: {e}")

def stop_cloudflared():
    """Detiene cloudflared al cerrar Flask"""
    global cloudflared_process
    if cloudflared_process:
        print("\n🛑 Deteniendo túnel...")
        cloudflared_process.terminate()
        try:
            cloudflared_process.wait(timeout=5)
        except:
            cloudflared_process.kill()

def generate_qr(url):
    """Genera un código QR con la URL del túnel"""
    
    if not QR_AVAILABLE:
        print("⚠️  No se puede generar QR (librería no instalada)")
        return
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Crear imagen con colores de Hogwarts
        img = qr.make_image(fill_color="#1a1410", back_color="#d4af37")
        
        qr_path = os.path.join('static', 'tunnel_qr.png')
        img.save(qr_path)
        global QR_TIMESTAMP
        QR_TIMESTAMP = int(time.time())
        print(f"📱 QR guardado en: {qr_path}")
        
    except Exception as e:
        print(f"❌ Error generando QR: {e}")

# ==========================================
# RUTAS
# ==========================================
@app.route('/')
@app.route('/subir')
def upload_page():
    return render_template('upload.html', tunnel_url=TUNNEL_URL)

@app.route('/galeria')
def gallery():
    return render_template('gallery.html')

@app.route('/videos')
def list_videos():
    videos = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(filename):
            title_file = os.path.join(app.config['UPLOAD_FOLDER'], filename + '.title')
            if os.path.exists(title_file):
                with open(title_file, 'r', encoding='utf-8') as f:
                    title = f.read().strip()
            else:
                title = "Retrato Mágico"
            
            videos.append({
                'filename': filename,
                'url': f'/static/videos/{filename}',
                'title': title
            })
    
    videos_with_time = []
    for v in videos:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], v['filename'])
        v['mtime'] = os.path.getmtime(filepath)
        videos_with_time.append(v)
    videos_with_time.sort(key=lambda x: x['mtime'], reverse=True)
    
    return jsonify(videos_with_time)

@app.route('/qr-info')
def qr_info():
    """Devuelve la URL del túnel y un timestamp para cache-busting"""
    return jsonify({
        'url': TUNNEL_URL,
        'timestamp': QR_TIMESTAMP
    })

@app.route('/upload', methods=['POST'])
def upload_video():
    print(f"\n📥 [UPLOAD] Nueva petición")
    
    if 'video' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo'}), 400
    
    file = request.files['video']
    author = request.form.get('author', 'Mago Anónimo')
    title = request.form.get('title', 'Retrato Mágico')
    
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            if not filename:
                filename = f"retrato_{int(time.time())}.webm"
            else:
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{int(time.time())}{ext}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            print(f"✅ [UPLOAD] Guardado: {filename} ({os.path.getsize(filepath)/1024/1024:.2f} MB)")
            
            with open(filepath + '.author', 'w', encoding='utf-8') as f:
                f.write(author)
            with open(filepath + '.title', 'w', encoding='utf-8') as f:
                f.write(title)
            
            return jsonify({'success': True, 'filename': filename})
            
        except Exception as e:
            print(f"❌ [UPLOAD] ERROR: {str(e)}")
            return jsonify({'error': f'Error al guardar: {str(e)}'}), 500
    
    return jsonify({'error': 'Formato no permitido'}), 400

# ==========================================
# INICIO
# ==========================================
if __name__ == '__main__':
    print("🏰 ¡El Castillo de Hogwarts está abierto!")
    print("🖼️  PARA TI (Local): http://localhost:5000/galeria")
    print("📤 PARA INVITAR: Espera a que se genere el túnel...")
    
    # Iniciar túnel automáticamente
    start_cloudflared()
    
    # Dar tiempo para que cloudflared genere la URL
    time.sleep(3)
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)