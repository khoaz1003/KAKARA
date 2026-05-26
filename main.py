import sys
import os
import random
import threading
import ctypes
import speech_recognition as sr
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import *
from yt_dlp import YoutubeDL

try:
    import requests
except ImportError:
    pass

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

myappid = 'mycompany.myproduct.subproduct.version' 
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--autoplay-policy=no-user-gesture-required"

STYLE = """
    QMainWindow { background: transparent; }
    #Header { background: rgba(0, 0, 0, 0.98); padding: 10px 30px; border-bottom: 3px solid #ff1744; }
    
    QLineEdit { 
        background-color: #1a1a1a; border-radius: 25px; padding: 12px 30px; 
        color: white; border: 2px solid #444; font-size: 18px;
    }

    #ControlBar { background: rgba(0, 0, 0, 0.95); border-bottom: 1px solid #333; }
    #ExitBtn { background: #ff1744; color: white; border: none; font-size: 14px; font-weight: bold; border-radius: 5px; padding: 8px 15px; }
    #GuideLabel { color: #888; font-size: 13px; }

    #ModernDialog { background-color: #111111; border: 3px solid #ff1744; border-radius: 20px; }
    #ScorePopup { background-color: #0c0c0c; border: 5px solid #ffd700; border-radius: 40px; }
    
    #VideoCard { background-color: rgba(20, 20, 20, 0.9); border-radius: 12px; border: 1px solid #222; }
    #VideoCard:hover { border: 1px solid #ff1744; background: #252525; }
    
    QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
"""

class Bridge(QObject):
    videoEnded = pyqtSignal()
    @pyqtSlot()
    def triggerEnd(self): self.videoEnded.emit()

class ScorePopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint); self.setFixedSize(700, 600)
        self.setObjectName("ScorePopup"); self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self); layout.setAlignment(Qt.AlignCenter)
        title = QLabel("SỐ ĐIỂM CỦA BẠN"); title.setStyleSheet("color: #ffd700; font-size: 30px; font-weight: bold;"); title.setAlignment(Qt.AlignCenter)
        self.lbl_score = QLabel("0"); self.lbl_score.setStyleSheet("color: #ff1744; font-size: 150px; font-weight: bold;"); self.lbl_score.setAlignment(Qt.AlignCenter)
        self.lbl_msg = QLabel("Chúc mừng bạn đã hoàn thành lượt hát!"); self.lbl_msg.setStyleSheet("color: white; font-size: 20px;"); self.lbl_msg.setAlignment(Qt.AlignCenter)
        self.lbl_grade = QLabel(""); self.lbl_grade.setAlignment(Qt.AlignCenter)
        self.btn_close = QPushButton("CHỌN BÀI KHÁC"); self.btn_close.setFixedSize(250, 55); self.btn_close.setStyleSheet("background: #ffd700; color: black; font-size: 18px; font-weight: bold; border-radius: 10px;"); self.btn_close.clicked.connect(self.close); self.btn_close.hide()
        layout.addStretch(); layout.addWidget(title); layout.addWidget(self.lbl_score); layout.addWidget(self.lbl_msg); layout.addWidget(self.lbl_grade); layout.addStretch(); layout.addWidget(self.btn_close, 0, Qt.AlignCenter); layout.addStretch()
        if random.random() < 0.3: self.target = random.randint(25, 49)
        else: self.target = random.randint(75, 100)
        self.current_step = 0; self.timer = QTimer(); self.timer.timeout.connect(self.run_score); self.timer.start(40)
    def run_score(self):
        if self.current_step < 35: self.lbl_score.setText(str(random.randint(25, 99))); self.current_step += 1
        else:
            self.timer.stop(); self.lbl_score.setText(str(self.target))
            color = "#555555" if self.target < 50 else "#00ff00"
            self.lbl_score.setStyleSheet(f"color: {color}; font-size: 160px; font-weight: bold;")
            self.lbl_grade.setStyleSheet(f"color: {'#ff4444' if self.target < 50 else '#00e5ff'}; font-size: 70px; font-weight: bold;")
            self.lbl_grade.setText("HÁT HƠI TỆ!" if self.target < 50 else random.choice(["QUÁ ĐỈNH CAO!", "GIỌNG HÁT VÀNG!"]))
            self.btn_close.show()

class SimpleSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setAttribute(Qt.WA_TransparentForMouseEvents); self.hide(); self.angle = 0
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_anim); self.timer.start(35)
    def update_anim(self): self.angle = (self.angle + 15) % 360; self.update()
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setPen(QPen(QColor("#ff1744"), 6))
        rect = QRect((self.width() - 80) // 2, (self.height() - 80) // 2, 80, 80); p.drawArc(rect, -self.angle * 16, 270 * 16)

class KzKaraoke(QMainWindow):
    search_done = pyqtSignal(list)
    voice_done = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("KAKARA - beta 1.1")
        self.setWindowIcon(QIcon(resource_path("appicon.png")))
        self.spinner = SimpleSpinner(self)
        self.initUI()
        self.search_done.connect(self.display_results); self.voice_done.connect(self.handle_voice_result)
        self.showMaximized()
        QTimer.singleShot(500, self.show_welcome)

    def show_exit_dialog(self):
        box = QDialog(self)
        box.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        box.setObjectName("ModernDialog")
        box.setStyleSheet(STYLE)
        box.setFixedSize(550, 300)
        l = QVBoxLayout(box)
        l.setContentsMargins(30, 40, 30, 40)
        t = QLabel("THOÁT")
        t.setStyleSheet("color: #ff1744; font-size: 28px; font-weight: bold;")
        t.setAlignment(Qt.AlignCenter)
        c = QLabel("Bạn có chắc chắn muốn thoát không?")
        c.setStyleSheet("color: white; font-size: 18px;")
        c.setWordWrap(True)
        c.setAlignment(Qt.AlignCenter)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        b_exit = QPushButton("Có, hẹn gặp lại!")
        b_exit.setFixedSize(180, 50)
        b_exit.setStyleSheet("background: #ff1744; color: white; font-weight: bold; border-radius: 12px; font-size: 16px;")
        b_exit.clicked.connect(qApp.quit) 
        
        b_stay = QPushButton("Không, ở lại hát tiếp")
        b_stay.setFixedSize(180, 50)
        b_stay.setStyleSheet("background: #444444; color: white; font-weight: bold; border-radius: 12px; font-size: 16px;")
        b_stay.clicked.connect(box.reject) 
        
        btn_layout.addWidget(b_exit)
        btn_layout.addWidget(b_stay)
        l.addWidget(t); l.addSpacing(15); l.addWidget(c); l.addStretch(); l.addLayout(btn_layout)
        return box.exec_()

    def closeEvent(self, event):
        event.ignore(); self.show_exit_dialog()

    def show_welcome(self): 
        msg = "Chào mừng bạn đến với KAKARA!\nPhần mềm Karaoke chấm điểm không quảng cáo top 1 vũ trụ"
        box = QDialog(self); box.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint); box.setObjectName("ModernDialog"); box.setStyleSheet(STYLE); box.setFixedSize(650, 450)
        l = QVBoxLayout(box); l.setContentsMargins(30, 30, 30, 30)
        
        t = QLabel("XIN CHÀO!"); t.setStyleSheet("color: #ff1744; font-size: 30px; font-weight: bold;"); t.setAlignment(Qt.AlignCenter)
        c = QLabel(msg); c.setStyleSheet("color: white; font-size: 19px;"); c.setWordWrap(True); c.setAlignment(Qt.AlignCenter)
        
        img_label = QLabel()
        pix = QPixmap(resource_path("wel.png"))  
        if not pix.isNull():
            # Thay đổi cách scale ảnh chào mừng: Ép ảnh giãn dài theo chiều ngang hoàn toàn
            img_label.setPixmap(pix.scaled(360, 238, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        img_label.setAlignment(Qt.AlignCenter)
        
        b = QPushButton("Cùng hát nào!"); b.setFixedSize(220, 55); b.setStyleSheet("background: #ff1744; color: white; font-weight: bold; border-radius: 12px; font-size: 16px;"); b.clicked.connect(box.accept)
        
        l.addWidget(img_label)
        l.addSpacing(10)
        l.addWidget(t)
        l.addSpacing(10)
        l.addWidget(c)
        l.addStretch()
        l.addWidget(b, 0, Qt.AlignCenter)
        box.exec_()

    def show_settings(self):
        box = QDialog(self); box.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint); box.setObjectName("ModernDialog"); box.setStyleSheet(STYLE); box.setFixedSize(550, 350)
        l = QVBoxLayout(box); l.setContentsMargins(30, 40, 30, 40)
        t = QLabel("Giới thiệu"); t.setStyleSheet("color: #ff1744; font-size: 30px; font-weight: bold;"); t.setAlignment(Qt.AlignCenter)
        c = QLabel("• Phiên bản KAKARA: dev beta 1.1\n• Nhà phát triển: khoaz1003\n• Nguồn video: youtube.com"); c.setStyleSheet("color: white; font-size: 19px;"); c.setAlignment(Qt.AlignCenter)
        b = QPushButton("OK"); b.setFixedSize(220, 55); b.setStyleSheet("background: #ff1744; color: white; font-weight: bold; border-radius: 12px; font-size: 16px;"); b.clicked.connect(box.accept)
        l.addWidget(t); l.addSpacing(20); l.addWidget(c); l.addStretch(); l.addWidget(b, 0, Qt.AlignCenter); box.exec_()

    def handle_voice_result(self, text):
        if text: self.input.setText(text); self.search()
        else: self.input.setPlaceholderText("Nhập tên hoặc bấm mic nói tên bài hát rồi nhấn Enter...")

    def paintEvent(self, event):
        p = QPainter(self); pix = QPixmap(resource_path("back.jpg"))  
        if not pix.isNull(): p.drawPixmap(self.rect(), pix)

    def resizeEvent(self, event):
        self.spinner.setGeometry(self.rect()); super().resizeEvent(event)

    def initUI(self):
        self.setStyleSheet(STYLE); self.stack = QStackedWidget(); self.setCentralWidget(self.stack)
        self.search_page = QWidget(); l = QVBoxLayout(self.search_page); l.setContentsMargins(0,0,0,0); l.setSpacing(0)
        header = QFrame(); header.setObjectName("Header"); hl = QHBoxLayout(header); header.setFixedHeight(110) 
        self.logo = QLabel(); pix = QPixmap(resource_path("logo.png"))  
        if not pix.isNull(): self.logo.setPixmap(pix.scaledToHeight(100, Qt.SmoothTransformation))
        self.input = QLineEdit(); self.input.setPlaceholderText("Nhập tên hoặc bấm mic nói tên bài hát rồi nhấn Enter...")
        self.input.returnPressed.connect(self.search)
        self.btn_mic = QPushButton(); self.btn_mic.setFixedSize(65, 65); self.btn_mic.setStyleSheet("background: transparent;")
        self.btn_mic.setIcon(QIcon(resource_path("mic.png"))); self.btn_mic.setIconSize(QSize(45, 45)); self.btn_mic.clicked.connect(self.start_voice)  
        self.btn_set = QPushButton(); self.btn_set.setFixedSize(65, 65); self.btn_set.setStyleSheet("background: transparent;")
        self.btn_set.setIcon(QIcon(resource_path("set.png"))); self.btn_set.setIconSize(QSize(45, 45)); self.btn_set.clicked.connect(self.show_settings)  
        
        self.btn_quit_app = QPushButton("THOÁT")
        self.btn_quit_app.setFixedSize(110, 48)
        self.btn_quit_app.setStyleSheet("background: #ff1744; color: white; font-weight: bold; border-radius: 12px; font-size: 15px;")
        self.btn_quit_app.clicked.connect(self.show_exit_dialog) 
        
        hl.addWidget(self.logo); hl.addSpacing(40); hl.addWidget(self.input, 1); hl.addSpacing(25); hl.addWidget(self.btn_mic); hl.addWidget(self.btn_set); hl.addSpacing(10); hl.addWidget(self.btn_quit_app)
        l.addWidget(header)
        
        self.scroll = QScrollArea(); self.scroll_content = QWidget(); self.grid = QGridLayout(self.scroll_content); self.grid.setSpacing(25); self.grid.setContentsMargins(25, 25, 25, 25)
        self.scroll.setWidget(self.scroll_content); self.scroll.setWidgetResizable(True); l.addWidget(self.scroll); self.stack.addWidget(self.search_page)

        self.video_page = QWidget(); vl = QVBoxLayout(self.video_page); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)
        self.ctrl_bar = QFrame(); self.ctrl_bar.setFixedHeight(60); self.ctrl_bar.setObjectName("ControlBar"); cl = QHBoxLayout(self.ctrl_bar)
        
        btn_exit = QPushButton("CHUYỂN BÀI"); btn_exit.setObjectName("ExitBtn"); btn_exit.clicked.connect(self.stop_video)
        cl.addWidget(btn_exit); cl.addSpacing(20)
        lbl_f11 = QLabel("Nhấn F11 để vào/thoát chế độ toàn màn hình.")
        lbl_f11.setStyleSheet("color: #888; font-size: 13px;")
        cl.addWidget(lbl_f11); cl.addStretch()
        lbl_esc = QLabel("KAKARA - Còn thở là còn hát")
        lbl_esc.setStyleSheet("color: #888; font-size: 13px;")
        cl.addWidget(lbl_esc)
        self.browser = QWebEngineView(); self.bridge = Bridge(); self.bridge.videoEnded.connect(self.show_score); self.channel = QWebChannel(); self.channel.registerObject('pyBridge', self.bridge); self.browser.page().setWebChannel(self.channel)
        vl.addWidget(self.ctrl_bar); vl.addWidget(self.browser); self.stack.addWidget(self.video_page)

    def start_voice(self):
        self.input.setText(""); self.input.setPlaceholderText("Đang nghe...") 
        threading.Thread(target=self.bg_voice, daemon=True).start()

    def bg_voice(self):
        r = sr.Recognizer()
        with sr.Microphone() as src:
            try:
                audio = r.listen(src, timeout=4, phrase_time_limit=5)
                text = r.recognize_google(audio, language="vi-VN")
                self.voice_done.emit(text)
            except: self.voice_done.emit("")

    def search(self):
        query = self.input.text()
        if query: 
            for i in reversed(range(self.grid.count())):
                w = self.grid.itemAt(i).widget()
                if w: w.setParent(None)
            self.spinner.show(); threading.Thread(target=self.bg_search, args=(query,), daemon=True).start()

    def bg_search(self, query):
        try:
            with YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                res = ydl.extract_info(f"ytsearch50:{query} karaoke", download=False)
                self.search_done.emit(res['entries'])
        except: self.search_done.emit([])

    def display_results(self, entries):
        self.spinner.hide()
        for i, vid in enumerate(entries):
            card = QFrame(); card.setObjectName("VideoCard"); card.setFixedWidth(280); cl = QVBoxLayout(card)
            img = QLabel(); img.setFixedSize(260, 145); img.setScaledContents(True); img.setCursor(Qt.PointingHandCursor)
            try:
                px = QPixmap(); px.loadFromData(requests.get(f"https://img.youtube.com/vi/{vid['id']}/mqdefault.jpg", timeout=5).content)
                img.setPixmap(px)
            except: pass
            img.mousePressEvent = lambda e, v=vid['id'], t=vid['title']: self.play(v, t)
            t_label = QLabel(vid['title']); t_label.setStyleSheet("color:white; font-weight:bold; font-size: 13px;"); t_label.setWordWrap(True); t_label.setFixedHeight(40)
            cl.addWidget(img); cl.addWidget(t_label); self.grid.addWidget(card, i // 5, i % 5)

    def play(self, v_id, v_title):
        clean_title = v_title.replace('"', '').replace("'", "")
        run_text = f"ĐANG PHÁT: <strong>\"{clean_title}\"</strong> 🎶🎶🎶 Chào mừng bạn đến với KAKARA - Chúc các bạn có một buổi hát vui vẻ!"

        html = f"""
        <html>
        <head>
        <style>
            html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background: #000; overflow: hidden; font-family: sans-serif; }}
            #player {{ width: 100%; height: 100%; position: absolute; top: 0; left: 0; z-index: 1; }}
            
            .ytp-caption-window-container, .caption-window, .ytp-captions-player-element {{
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
            }}

            .news-marquee {{
                position: absolute;
                bottom: 0px; 
                left: 0;
                width: 100%;
                background: rgba(0, 0, 0, 0.88); 
                color: #ffffff;
                font-size: 22px; 
                font-weight: normal;
                padding: 10px 0; 
                white-space: nowrap;
                overflow: hidden;
                z-index: 9999;
                pointer-events: none;
                border-top: 2px solid rgba(255, 23, 68, 0.7);
                display: none; 
            }}
            .news-marquee span {{
                display: inline-block;
                padding-left: 100%;
                animation: marquee 28s linear forwards; 
            }}
            .news-marquee strong {{
                font-weight: 900;
                color: #ffffff;
            }}
            @keyframes marquee {{
                0%   {{ transform: translate(0, 0); }}
                100% {{ transform: translate(-100%, 0); }}
            }}

            .watermark {{
                position: absolute;
                top: 15px;
                left: 15px;
                color: rgba(255, 255, 255, 0.25);
                font-size: 67px;
                font-weight: bold;
                letter-spacing: 2px;
                z-index: 9999;
                pointer-events: none;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.6);
            }}
        </style>
        </head>
        <body>
            <div id="player"></div>
            <div class="watermark">KAKARA</div>
            
            <div class="news-marquee" id="marqueeBox">
                <span>{run_text}</span>
            </div>

            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <script>
                var pyBridge;
                new QWebChannel(qt.webChannelTransport, function(ch) {{
                    pyBridge = ch.objects.pyBridge;
                }});

                var tag = document.createElement('script');
                tag.src = 'https://www.youtube.com/iframe_api';
                document.head.appendChild(tag);

                function onYouTubeIframeAPIReady() {{
                    new YT.Player('player', {{
                        height: '100%',
                        width: '100%',
                        videoId: '{v_id}',
                        playerVars: {{ 
                            'autoplay': 1, 
                            'controls': 1, 
                            'cc_load_policy': 0, 
                            'iv_load_policy': 3,
                            'hl': 'vi'
                        }},
                        events: {{
                            'onStateChange': function(e) {{
                                if(e.data === 0) pyBridge.triggerEnd();
                            }}
                        }}
                    }});
                }}

                window.addEventListener('keydown', function(e) {{
                    if (e.key === 'c' || e.key === 'C' || e.keyCode === 67) {{
                        e.stopImmediatePropagation();
                        e.preventDefault();
                    }}
                }}, true);

                setTimeout(function() {{
                    var box = document.getElementById('marqueeBox');
                    if(box) box.style.display = 'block';
                }}, 2000);

                setTimeout(function() {{
                    var box = document.getElementById('marqueeBox');
                    if(box) box.style.display = 'none';
                }}, 30000);

                setInterval(function() {{
                    var captions = document.querySelectorAll('.ytp-caption-window-container, .caption-window, .ytp-captions-player-element');
                    captions.forEach(function(el) {{
                        el.style.setProperty('display', 'none', 'important');
                    }});
                }}, 300);
            </script>
        </body>
        </html>
        """
        self.browser.setHtml(html, QUrl("http://localhost"))
        self.stack.setCurrentIndex(1)

    def show_score(self): 
        ScorePopup(self).exec_()
        self.stop_video()

    def stop_video(self): 
        self.browser.setHtml("")
        self.stack.setCurrentIndex(0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            if self.isFullScreen(): self.showMaximized()
            else: self.showFullScreen()
        elif event.key() == Qt.Key_Escape: self.showMaximized()
        super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv); QWebEngineProfile.defaultProfile().setHttpUserAgent("Mozilla/5.0")
    window = KzKaraoke(); sys.exit(app.exec_())