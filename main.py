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
import json
import requests

try:
    from yt_dlp import YoutubeDL
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    from yt_dlp import YoutubeDL

class InternetRemoteThread(QThread):
    command_received = pyqtSignal(str, str)

    def __init__(self, room_code):
        super().__init__()
        self.room_code = room_code
        self.running = True

    def run(self):
        url = f"https://ntfy.sh/kakara_room_{self.room_code}/json"
        try:
            response = requests.get(url, stream=True, timeout=60)
            for line in response.iter_lines():
                if not self.running: break
                if line:
                    data = json.loads(line.decode('utf-8'))
                    if "message" in data:
                        try:
                            cmd = json.loads(data["message"])
                            self.command_received.emit(cmd["action"], cmd["value"])
                        except:
                            pass
        except:
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
    /* 2. THANH SIDEBAR TRÊN CÙNG Ở CHẾ ĐỘ ĐIỀU KHIỂN TRONG SUỐT (45%) */
    #Header { background: rgba(0, 0, 0, 0.45); padding: 10px 30px; border-bottom: 3px solid #ff1744; }
    
    QLineEdit { 
        background-color: #1a1a1a; border-radius: 25px; padding: 12px 30px; 
        color: white; border: 2px solid #444; font-size: 18px;
    }
    
    #ControlBar { background: rgba(0, 0, 0, 0.95); border-bottom: 1px solid #333; }
    
    #ExitBtn { 
        background: #ff1744; color: white; border: none; font-size: 14px; 
        font-weight: bold; border-radius: 20px; padding: 8px 22px; height: 36px;
    }
    #ExitBtn:hover { background: #ff4466; }
    
    /* 1. CHỈNH NÚT THU NHỎ THÀNH CHỮ, MÀU ĐỎ, NẰM NGOÀI CÙNG BÊN TRÁI */
    #MinimizeBarBtn { 
        background: #ff1744; color: white; border: none; font-size: 13px; 
        font-weight: bold; border-radius: 6px; padding: 0px 15px; height: 36px;
    }
    #MinimizeBarBtn:hover { background: #ff4466; }
    
    #FullscreenBtn { 
        background: #00e5ff; color: black; border: none; font-size: 13px; 
        font-weight: bold; border-radius: 6px; padding: 0px 15px; height: 36px;
    }
    #FullscreenBtn:hover { background: #66efff; }
    
    #FloatingMenuBtn { 
        background: rgba(255, 23, 68, 0.85); color: white; border: none; 
        border-radius: 22px; font-size: 22px; font-weight: bold;
    }
    #FloatingMenuBtn:hover { background: #ff1744; }
    
    #ModernDialog { background-color: #111111; border: 3px solid #ff1744; border-radius: 20px; }
    #ScorePopup { background-color: #0c0c0c; border: 5px solid #ffd700; border-radius: 40px; }
    
    #VideoCard { background-color: rgba(20, 20, 20, 0.9); border-radius: 12px; border: 1px solid #222; }
    #VideoCard:hover { border: 1px solid #ff1744; background: #252525; }
    
    QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
"""

class DraggableBaseDialog(QDialog):
    def __init__(self, parent=None, can_drag=True):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.can_drag = can_drag
        self._drag_position = QPoint()

        if parent:
            self.center_on_parent(parent)

    def center_on_parent(self, parent):
        parent_geo = parent.geometry()
        if parent.isFullScreen() or parent.isMaximized():
            screen = QApplication.desktop().screenGeometry(parent)
            parent_x = screen.x()
            parent_y = screen.y()
            parent_w = screen.width()
            parent_h = screen.height()
        else:
            parent_x = parent_geo.x()
            parent_y = parent_geo.y()
            parent_w = parent_geo.width()
            parent_h = parent_geo.height()

        # Tính toán tọa độ trung tâm tuyệt đối
        self.adjustSize()
        x = parent_x + (parent_w - self.width()) // 2
        y = parent_y + (parent_h - self.height()) // 2
        self.move(x, y)

    def mousePressEvent(self, event):
        if self.can_drag and event.button() == Qt.LeftButton:
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.can_drag and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_position)
            event.accept()


class ModeToggleSwitch(QWidget):
    modeChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 50)
        self.current_mode = 0  

        self.lbl_local = QLabel("Chế độ độc lập", self)
        self.lbl_local.setGeometry(0, 0, 200, 50)
        self.lbl_local.setAlignment(Qt.AlignCenter)
        self.lbl_local.setStyleSheet("color: #000; font-size: 14px; font-weight: bold; background: transparent;")

        self.lbl_remote = QLabel("Chế độ phòng hát", self)
        self.lbl_remote.setGeometry(200, 0, 200, 50)
        self.lbl_remote.setAlignment(Qt.AlignCenter)
        self.lbl_remote.setStyleSheet("color: #888; font-size: 14px; font-weight: bold; background: transparent;")

        self.thumb = QWidget(self)
        self.thumb.setGeometry(0, 0, 200, 50) 
        self.thumb.setStyleSheet("background-color: #00e5ff; border-radius: 10px;")

        self.lbl_local.raise_()
        self.lbl_remote.raise_()

        self.anim = QPropertyAnimation(self.thumb, b"pos")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#222222"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)

    def mousePressEvent(self, event):
        if event.x() < 200 and self.current_mode != 0:
            self.setMode(0)
        elif event.x() >= 200 and self.current_mode != 1:
            self.setMode(1)

    def setMode(self, mode):
        self.current_mode = mode
        if mode == 0:
            self.anim.setEndValue(QPoint(0, 0))
            self.lbl_local.setStyleSheet("color: #000; font-size: 14px; font-weight: bold;")
            self.lbl_remote.setStyleSheet("color: #888; font-size: 14px; font-weight: bold;")
        else:
            self.anim.setEndValue(QPoint(200, 0))
            self.lbl_local.setStyleSheet("color: #888; font-size: 14px; font-weight: bold;")
            self.lbl_remote.setStyleSheet("color: #000; font-size: 14px; font-weight: bold;")
        self.anim.start()
        self.modeChanged.emit(mode)

class Bridge(QObject):
    videoEnded = pyqtSignal()
    @pyqtSlot()
    def triggerEnd(self):
        self.videoEnded.emit()

# POPUP ĐIỂM SỐ: Kế thừa DraggableBaseDialog nhưng đặt can_drag=False để KHÔNG cho kéo thả
class ScorePopup(DraggableBaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent, can_drag=False)
        self.setFixedSize(700, 600)
        self.setObjectName("ScorePopup")
        self.setStyleSheet(STYLE)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("SỐ ĐIỂM CỦA BẠN")
        title.setStyleSheet("color: #ffd700; font-size: 30px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        
        self.lbl_score = QLabel("0")
        self.lbl_score.setStyleSheet("color: #ff1744; font-size: 150px; font-weight: bold;")
        self.lbl_score.setAlignment(Qt.AlignCenter)
        
        self.lbl_msg = QLabel("Chúc mừng bạn đã hoàn thành lượt hát!")
        self.lbl_msg.setStyleSheet("color: white; font-size: 20px;")
        self.lbl_msg.setAlignment(Qt.AlignCenter)
        
        self.lbl_grade = QLabel("")
        self.lbl_grade.setAlignment(Qt.AlignCenter)
        
        self.btn_close = QPushButton("TIẾP TỤC HÁT")
        self.btn_close.setFixedSize(250, 55)
        self.btn_close.setStyleSheet("background: #ffd700; color: black; font-size: 18px; font-weight: bold; border-radius: 10px;")
        self.btn_close.clicked.connect(self.close)
        self.btn_close.hide()
        
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(self.lbl_score)
        layout.addWidget(self.lbl_msg)
        layout.addWidget(self.lbl_grade)
        layout.addStretch()
        layout.addWidget(self.btn_close, 0, Qt.AlignCenter)
        layout.addStretch()
        
        if random.random() < 0.3:
            self.target = random.randint(25, 49)
        else:
            self.target = random.randint(75, 100)
            
        self.current_step = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_score)
        self.timer.start(40)
        
        # Gọi lại căn giữa sau khi dựng đủ Widget
        if parent: self.center_on_parent(parent)

    def run_score(self):
        if self.current_step < 35:
            self.lbl_score.setText(str(random.randint(25, 99)))
            self.current_step += 1
        else:
            self.timer.stop()
            self.lbl_score.setText(str(self.target))
            if self.target < 50:
                self.lbl_score.setStyleSheet("color: #555555; font-size: 160px; font-weight: bold;")
                self.lbl_grade.setStyleSheet("color: #ff4444; font-size: 70px; font-weight: bold;")
                self.lbl_grade.setText("HÁT HƠI TỆ!")
            else:
                self.lbl_score.setStyleSheet("color: #00ff00; font-size: 160px; font-weight: bold;")
                self.lbl_grade.setStyleSheet("color: #00e5ff; font-size: 70px; font-weight: bold;")
                self.lbl_grade.setText(random.choice(["QUÁ ĐỈNH CAO!", "GIỌNG HÁT VÀNG!"]))
            self.btn_close.show()

class SimpleSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()
        self.angle = 0
        self.timer = QTimer(self)
        self.timeout = self.timer.timeout.connect(self.update_anim)
        self.timer.start(35)
        
    def update_anim(self):
        self.angle = (self.angle + 15) % 360
        self.update()
        
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#ff1744"), 6))
        rect = QRect((self.width() - 80) // 2, (self.height() - 80) // 2, 80, 80)
        p.drawArc(rect, -self.angle * 16, 270 * 16)

class KzKaraoke(QMainWindow):
    search_done = pyqtSignal(list)
    voice_done = pyqtSignal(str)
    def show_about(self):
        # Tạo dialog mới cho Giới thiệu
        dlg = QDialog(self)
        dlg.setWindowTitle("Giới thiệu")
        dlg.setFixedSize(300, 200)
        
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("KAKARA PC"))
        layout.addWidget(QLabel("Phiên bản: devbeta 1.3"))
        layout.addWidget(QLabel("Nhà phát triển: khoaz1003"))
        
        btn = QPushButton("OK")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        
        dlg.exec_()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("KAKARA - beta 1.3")
        self.setWindowIcon(QIcon(resource_path("appicon.png")))
        self.spinner = SimpleSpinner(self)
        
        self.pairing_code = str(random.randint(1000, 9999))
        self.remote_enabled = False 
        self.has_device_connected = False 
        
        self.remote_thread = InternetRemoteThread(self.pairing_code)
        self.remote_thread.command_received.connect(self.handle_cloud_command)
        self.remote_thread.start()

        self.initUI()
        self.search_done.connect(self.display_results)
        self.voice_done.connect(self.handle_voice_result)
        self.showMaximized()
        QTimer.singleShot(500, self.show_welcome)

    def handle_cloud_command(self, action, value):
        if not self.remote_enabled: return
        if not self.has_device_connected:
            self.has_device_connected = True
            
        if action == "skip":
            if self.stack.currentIndex() == 1:
                self.stop_video()
        elif action == "fullscreen":
            if self.stack.currentIndex() == 1:
                self.toggle_fullscreen_ui()
        elif action == "vol_up":
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
        elif action == "vol_down":
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
        elif action == "show_code":
            self.show_code_popup()
        elif action == "play_direct":
            try:
                vid_info = json.loads(value)
                self.play(vid_info["id"], vid_info["title"])
            except:
                pass
        elif action == "request_search":
            threading.Thread(target=self.bg_cloud_search, args=(value,), daemon=True).start()

    def bg_cloud_search(self, query):
        try:
            with YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                res = ydl.extract_info(f"ytsearch12:{query} karaoke", download=False)
                videos = [{"id": v["id"], "title": v["title"]} for v in res['entries'] if 'id' in v and 'title' in v]
                
                requests.post(
                    f"https://ntfy.sh/kakara_res_{self.pairing_code}", 
                    data=json.dumps(videos).encode('utf-8'), 
                    timeout=5
                )
        except Exception as e:
            print("Lỗi cào dữ liệu hoặc gửi trả kết quả:", e)

    def change_remote_mode(self, mode):
        if mode == 0:
            self.remote_enabled = False
            self.btn_dialog_close.setText("ĐÓNG")
        else:
            self.remote_enabled = True
            self.btn_dialog_close.setText("CHUYỂN")

    def update_main_ui_by_mode(self):
        if not self.remote_enabled:
            self.logo.setPixmap(QPixmap(resource_path("logo.png")).scaledToHeight(100, Qt.SmoothTransformation))
            self.input.show()
            self.btn_mic.show()
            self.scroll.show()
            self.welcome_remote_widget.hide()
        else:
            self.logo.setPixmap(QPixmap(resource_path("logo.png")).scaledToHeight(130, Qt.SmoothTransformation)) 
            self.input.hide()
            self.btn_mic.hide()
            self.scroll.hide()
            self.welcome_remote_widget.show()

    def show_settings(self):
        box = DraggableBaseDialog(self, can_drag=True)
        box.setObjectName("ModernDialog")
        box.setStyleSheet(STYLE)
        box.setFixedSize(550, 400)
        box.center_on_parent(self) # Căn chính giữa app hiện tại
        
        l = QVBoxLayout(box)
        l.setContentsMargins(30, 25, 30, 25)
        l.setAlignment(Qt.AlignCenter)
        
        t = QLabel("CÀI ĐẶT HỆ THỐNG")
        t.setStyleSheet("color: #ff1744; font-size: 24px; font-weight: bold;")
        t.setAlignment(Qt.AlignCenter)
        l.addWidget(t)
        l.addSpacing(15)

        self.toggle_switch = ModeToggleSwitch(box)
        self.toggle_switch.setMode(1 if self.remote_enabled else 0)
        self.toggle_switch.modeChanged.connect(self.change_remote_mode)
        l.addWidget(self.toggle_switch, 0, Qt.AlignCenter)
        l.addSpacing(20)

        c = QLabel("• Chế độ độc lập: Chọn bài và hát karaoke trực tiếp trên máy tính.\n• Chế độ phòng hát: Sử dụng điện thoại/máy tính bảng vào webapp để kết nối và chọn bài hát hoặc điều khiển từ xa./n Link kết nối: COMING SOON")
        c.setStyleSheet("color: #aaaaaa; font-size: 14px;")
        c.setAlignment(Qt.AlignLeft)
        l.addWidget(c)
        l.addStretch()


        btn_about = QPushButton("Giới thiệu")
        btn_about.clicked.connect(self.show_about)
        l.addWidget(btn_about)

        self.btn_dialog_close = QPushButton(f"{'CHUYỂN' if self.remote_enabled else 'ĐÓNG'}")
        self.btn_dialog_close.setFixedSize(200, 48)
        self.btn_dialog_close.setStyleSheet("background: #ff1744; color: white; font-weight: bold; border-radius: 12px; font-size: 15px;")
        self.btn_dialog_close.clicked.connect(box.accept)
        l.addWidget(self.btn_dialog_close, 0, Qt.AlignCenter)
        
        if box.exec_() == QDialog.Accepted:
            self.update_main_ui_by_mode()
 
    def show_code_popup(self):
        popup = DraggableBaseDialog(self, can_drag=True)
        popup.setObjectName("ModernDialog")
        popup.setStyleSheet(STYLE)
        popup.setFixedSize(500, 320) # Thu nhỏ chiều cao lại một chút vì đã xóa bớt phần tử
        popup.center_on_parent(self) # Căn chính giữa app hiện tại

        vl = QVBoxLayout(popup)
        vl.setContentsMargins(25, 30, 25, 25)
        vl.setAlignment(Qt.AlignCenter)

        t = QLabel("MÃ PHÒNG KẾT NỐI ĐIỀU KHIỂN")
        t.setStyleSheet("color: white; font-size: 20px; font-weight: bold; letter-spacing: 1px;")
        t.setAlignment(Qt.AlignCenter)
        vl.addWidget(t)

        lbl_code = QLabel(self.pairing_code)
        lbl_code.setStyleSheet("color: #00e5ff; font-size: 75px; font-weight: 900; letter-spacing: 5px; margin: 15px 0;")
        lbl_code.setAlignment(Qt.AlignCenter)
        vl.addWidget(lbl_code)
        vl.addStretch()

        btn_close_pop = QPushButton("ĐÓNG")
        btn_close_pop.setFixedSize(180, 48)
        btn_close_pop.setStyleSheet("background: #ff1744; color: white; font-weight: bold; border-radius: 12px; font-size: 14px;")
        btn_close_pop.clicked.connect(popup.accept)

        vl.addWidget(btn_close_pop, 0, Qt.AlignCenter)

        popup.exec_()
        
        def regenerate_code():
            self.pairing_code = str(random.randint(1000, 9999))
            lbl_code.setText(self.pairing_code)
            self.has_device_connected = False
            self.remote_thread.running = False
            self.remote_thread.wait()
            self.remote_thread = InternetRemoteThread(self.pairing_code)
            self.remote_thread.command_received.connect(self.handle_cloud_command)
            self.remote_thread.start()


        btn_close_pop = QPushButton("ĐÓNG")
        btn_close_pop.setFixedSize(160, 48)
        btn_close_pop.setStyleSheet("background: #ff1744; color: white; font-weight: bold; border-radius: 12px; font-size: 14px;")
        btn_close_pop.clicked.connect(popup.accept)

        popup.exec_()

    def show_exit_dialog(self):
        box = DraggableBaseDialog(self, can_drag=True)
        box.setObjectName("ModernDialog")
        box.setStyleSheet(STYLE)
        box.setFixedSize(550, 300)
        box.center_on_parent(self) # Căn chính giữa app hiện tại
        
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
        
        l.addWidget(t)
        l.addSpacing(15)
        l.addWidget(c)
        l.addStretch()
        l.addLayout(btn_layout)
        
        return box.exec_()

    def closeEvent(self, event):
        event.ignore()
        self.show_exit_dialog()

    def show_welcome(self): 
        msg = "Chào mừng bạn đến với KAKARA!\nPhần mềm Karaoke chấm điểm không quảng cáo top 1 vũ trụ"
        box = DraggableBaseDialog(self, can_drag=True)
        box.setObjectName("ModernDialog")
        box.setStyleSheet(STYLE)
        box.setFixedSize(650, 450)
        box.center_on_parent(self) # Căn chính giữa app hiện tại
        
        l = QVBoxLayout(box)
        l.setContentsMargins(30, 30, 30, 30)
        
        t = QLabel("XIN CHÀO!")
        t.setStyleSheet("color: #ff1744; font-size: 30px; font-weight: bold;")
        t.setAlignment(Qt.AlignCenter)
        
        c = QLabel(msg)
        c.setStyleSheet("color: white; font-size: 19px;")
        c.setWordWrap(True)
        c.setAlignment(Qt.AlignCenter)
        
        img_label = QLabel()
        pix = QPixmap(resource_path("wel.png"))  
        if not pix.isNull():
            img_label.setPixmap(pix.scaled(360, 238, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        img_label.setAlignment(Qt.AlignCenter)
        
        b = QPushButton("Cùng hát nào!")
        b.setFixedSize(220, 55)
        b.setStyleSheet("background: #ff1744; color: white; font-weight: bold; border-radius: 12px; font-size: 16px;")
        b.clicked.connect(box.accept)
        
        l.addWidget(img_label)
        l.addSpacing(10)
        l.addWidget(t)
        l.addSpacing(10)
        l.addWidget(c)
        l.addStretch()
        l.addWidget(b, 0, Qt.AlignCenter)
        
        box.exec_()

    def handle_voice_result(self, text):
        if text:
            self.input.setText(text)
            self.search()
        else:
            self.input.setPlaceholderText("Nhập tên hoặc bấm mic nói tên bài hát rồi nhấn Enter...")

    def paintEvent(self, event):
        p = QPainter(self)
        pix = QPixmap(resource_path("back.jpg"))  
        if not pix.isNull():
            p.drawPixmap(self.rect(), pix)

    def resizeEvent(self, event):
        self.spinner.setGeometry(self.rect())
        self.btn_floating_menu.setGeometry(15, 12, 44, 44)
        super().resizeEvent(event)

    def initUI(self):
        self.setStyleSheet(STYLE)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        self.search_page = QWidget()
        self.main_layout = QVBoxLayout(self.search_page)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setSpacing(0)
        
        header = QFrame()
        header.setObjectName("Header")
        hl = QHBoxLayout(header)
        header.setFixedHeight(120) 
        
        self.logo = QLabel()
        pix = QPixmap(resource_path("logo.png"))  
        if not pix.isNull():
            self.logo.setPixmap(pix.scaledToHeight(100, Qt.SmoothTransformation))
            
        self.input = QLineEdit()
        self.input.setPlaceholderText("Nhập tên hoặc bấm mic nói tên bài hát rồi nhấn Enter...")
        self.input.returnPressed.connect(self.search)
        
        self.btn_mic = QPushButton()
        self.btn_mic.setFixedSize(65, 65)
        self.btn_mic.setStyleSheet("background: transparent;")
        self.btn_mic.setIcon(QIcon(resource_path("mic.png")))
        self.btn_mic.setIconSize(QSize(45, 45))
        self.btn_mic.clicked.connect(self.start_voice)  
        
        self.btn_set = QPushButton()
        self.btn_set.setFixedSize(65, 65)
        self.btn_set.setStyleSheet("background: transparent;")
        self.btn_set.setIcon(QIcon(resource_path("set.png")))
        self.btn_set.setIconSize(QSize(45, 45))
        self.btn_set.clicked.connect(self.show_settings)  
        
        self.btn_quit_app = QPushButton("THOÁT")
        self.btn_quit_app.setFixedSize(110, 48)
        self.btn_quit_app.setStyleSheet("background: #ff1744; color: white; font-weight: bold; border-radius: 12px; font-size: 15px;")
        self.btn_quit_app.clicked.connect(self.show_exit_dialog) 
        
        hl.addWidget(self.logo)
        hl.addSpacing(40)
        hl.addWidget(self.input, 1)
        hl.addSpacing(25)
        hl.addWidget(self.btn_mic)
        hl.addWidget(self.btn_set)
        hl.addSpacing(10)
        hl.addWidget(self.btn_quit_app)
        
        self.main_layout.addWidget(header)
        
        #CHẾ ĐỘ PHÒNG HÁT
        self.welcome_remote_widget = QWidget()
        wl = QVBoxLayout(self.welcome_remote_widget)
        wl.setAlignment(Qt.AlignCenter)
        wl.setSpacing(10)
        
        lbl_welcome = QLabel("CHÀO MỪNG BẠN ĐẾN VỚI PHÒNG HÁT KAKARA!")
        lbl_welcome.setStyleSheet("color: white; font-size: 38px; font-weight: bold; letter-spacing: 1px;")
        lbl_welcome.setAlignment(Qt.AlignCenter)
        
        lbl_sub = QLabel("Chế độ phòng hát - Nhấn nút tạo mã phòng và nhập mã vào webapp để kết nối điều khiển từ xa.")
        lbl_sub.setStyleSheet("color: #aaaaaa; font-size: 18px;")
        lbl_sub.setAlignment(Qt.AlignCenter)
        
        btn_generate_code = QPushButton("TẠO MÃ PHÒNG")
        btn_generate_code.setFixedSize(240, 55)
        btn_generate_code.setStyleSheet("background: #00e5ff; color: black; font-size: 16px; font-weight: bold; border-radius: 12px;")
        btn_generate_code.clicked.connect(self.show_code_popup)
        
        wl.addStretch()
        wl.addWidget(lbl_welcome)
        wl.addWidget(lbl_sub)
        wl.addSpacing(25)
        wl.addWidget(btn_generate_code, 0, Qt.AlignCenter)
        wl.addStretch()
        
        self.main_layout.addWidget(self.welcome_remote_widget)
        self.welcome_remote_widget.hide() 

        self.scroll = QScrollArea()
        self.scroll_content = QWidget()
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setSpacing(25)
        self.grid.setContentsMargins(25, 25, 25, 25)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll)
        
        self.stack.addWidget(self.search_page)

        # PAGE VIDEO PLAYBACK
        # PAGE VIDEO PLAYBACK
        self.video_page = QWidget()
        self.video_container = QGridLayout(self.video_page)
        self.video_container.setContentsMargins(0,0,0,0)
        self.video_container.setSpacing(0)
        
        self.ctrl_bar = QFrame()
        self.ctrl_bar.setFixedHeight(60)
        self.ctrl_bar.setObjectName("ControlBar")
        cl = QHBoxLayout(self.ctrl_bar)
        cl.setContentsMargins(15, 0, 15, 0)
        
        btn_min_bar = QPushButton("▼") 
        btn_min_bar.setObjectName("MinimizeBarBtn")
        btn_min_bar.clicked.connect(self.minimize_control_bar)
        cl.addWidget(btn_min_bar)
        cl.addSpacing(12)

        # 2. ĐƯA NÚT CHUYỂN BÀI NẰM SAU NÚT THU NHỎ
        btn_exit = QPushButton("CHUYỂN BÀI")
        btn_exit.setObjectName("ExitBtn")
        btn_exit.clicked.connect(self.stop_video)
        cl.addWidget(btn_exit)
        cl.addSpacing(12)
        
        self.btn_fullscreen = QPushButton("TOÀN MÀN HÌNH")
        self.btn_fullscreen.setObjectName("FullscreenBtn")
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen_ui)
        cl.addWidget(self.btn_fullscreen)
        cl.addSpacing(15)
        
        lbl_f11 = QLabel("                           ")
        lbl_f11.setStyleSheet("color: #888; font-size: 13px;")
        cl.addWidget(lbl_f11)
        cl.addStretch()
        
        lbl_esc = QLabel("KAKARA - Còn thở là còn hát")
        lbl_esc.setStyleSheet("color: #888; font-size: 13px;")
        cl.addWidget(lbl_esc)
        
        self.browser = QWebEngineView()
        self.bridge = Bridge()
        self.bridge.videoEnded.connect(self.show_score)
        self.channel = QWebChannel()
        self.channel.registerObject('pyBridge', self.bridge)
        self.browser.page().setWebChannel(self.channel)
        
        self.video_container.addWidget(self.browser, 0, 0, 2, 1)
        self.video_container.addWidget(self.ctrl_bar, 0, 0, 1, 1, Qt.AlignTop)
        self.stack.addWidget(self.video_page)
        
        self.btn_floating_menu = QPushButton("≡", self.video_page)
        self.btn_floating_menu.setObjectName("FloatingMenuBtn")
        self.btn_floating_menu.hide()
        self.btn_floating_menu.clicked.connect(self.restore_control_bar)

    def start_voice(self):
        self.input.setText("")
        self.input.setPlaceholderText("Đang nghe...") 
        threading.Thread(target=self.bg_voice, daemon=True).start()

    def bg_voice(self):
        r = sr.Recognizer()
        with sr.Microphone() as src:
            try:
                audio = r.listen(src, timeout=4, phrase_time_limit=5)
                text = r.recognize_google(audio, language="vi-VN")
                self.voice_done.emit(text)
            except:
                self.voice_done.emit("")

    def search(self):
        query = self.input.text()
        if query: 
            for i in reversed(range(self.grid.count())):
                w = self.grid.itemAt(i).widget()
                if w: w.setParent(None)
            self.spinner.show()
            threading.Thread(target=self.bg_search, args=(query,), daemon=True).start()

    def bg_search(self, query):
        try:
            with YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                res = ydl.extract_info(f"ytsearch50:{query} karaoke", download=False)
                self.search_done.emit(res['entries'])
        except:
            self.search_done.emit([])

    def display_results(self, entries):
        self.spinner.hide()
        for i, vid in enumerate(entries):
            if 'id' not in vid or 'title' not in vid: continue
            card = QFrame()
            card.setObjectName("VideoCard")
            card.setFixedWidth(280)
            cl = QVBoxLayout(card)
            
            img = QLabel()
            img.setFixedSize(260, 145)
            img.setScaledContents(True)
            img.setCursor(Qt.PointingHandCursor)
            try:
                px = QPixmap()
                px.loadFromData(requests.get(f"https://img.youtube.com/vi/{vid['id']}/mqdefault.jpg", timeout=5).content)
                img.setPixmap(px)
            except:
                pass
                
            img.mousePressEvent = lambda e, v=vid['id'], t=vid['title']: self.play(v, t)
            t_label = QLabel(vid['title'])
            t_label.setStyleSheet("color:white; font-weight:bold; font-size: 13px;")
            t_label.setWordWrap(True)
            t_label.setFixedHeight(40)
            
            cl.addWidget(img)
            cl.addWidget(t_label)
            self.grid.addWidget(card, i // 5, i % 5)

    def play(self, v_id, v_title):
        clean_title = v_title.replace('"', '').replace("'", "")
        run_text = f"ĐANG PHÁT: <strong>\"{clean_title}\"</strong> \u2014 --- Hệ thống hát karraoke KAKARA Beta 1.3 --- Chúc các bạn có 1 buổi hát vui vẻ!"

        html = f"""
        <html>
        <head>
        <style>
            html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background: #000; overflow: hidden; font-family: sans-serif; }}
            #player {{ width: 100%; height: 100%; position: absolute; top: 0; left: 0; z-index: 1; }}
            .ytp-caption-window-container, .caption-window, .ytp-captions-player-element {{ display: none !important; visibility: hidden !important; opacity: 0 !important; }}
            .news-marquee {{ position: absolute; bottom: 0px; left: 0; width: 100%; background: rgba(0, 0, 0, 0.88); color: #ffffff; font-size: 22px; padding: 10px 0; white-space: nowrap; overflow: hidden; z-index: 9999; pointer-events: none; border-top: 2px solid rgba(255, 23, 68, 0.7); display: none; }}
            .news-marquee span {{ display: inline-block; padding-left: 100%; animation: marquee 28s linear forwards; }}
            @keyframes marquee {{ 0% {{ transform: translate(0, 0); }} 100% {{ transform: translate(-100%, 0); }} }}
        </style>
        </head>
        <body>
            <div id="player"></div>
            <div class="news-marquee" id="marqueeBox"><span>{run_text}</span></div>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <script>
                var pyBridge;
                new QWebChannel(qt.webChannelTransport, function(ch) {{ pyBridge = ch.objects.pyBridge; }});
                var tag = document.createElement('script'); tag.src = 'https://www.youtube.com/iframe_api'; document.head.appendChild(tag);
                function onYouTubeIframeAPIReady() {{
                    new YT.Player('player', {{
                        height: '100%', width: '100%', videoId: '{v_id}',
                        playerVars: {{ 'autoplay': 1, 'controls': 1, 'cc_load_policy': 0, 'iv_load_policy': 3, 'hl': 'vi' }},
                        events: {{ 'onStateChange': function(e) {{ if(e.data === 0) pyBridge.triggerEnd(); }} }}
                    }});
                }}
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
        self.ctrl_bar.hide()           
        self.btn_floating_menu.show()   
        self.btn_floating_menu.raise_() 
        self.browser.setHtml(html, QUrl("http://localhost"))
        self.stack.setCurrentIndex(1)

    def show_score(self): 
        self.score_popup = ScorePopup(self)
        self.score_popup.exec_()
        self.stop_video()

    def stop_video(self): 
        # Nếu bảng điểm đang mở thì chủ động đóng nó luôn
        if hasattr(self, 'score_popup') and self.score_popup:
            try:
                self.score_popup.close()
            except Exception as e:
                print("Lỗi đóng popup:", e)
            self.score_popup = None
            
        self.browser.setHtml("")
        self.stack.setCurrentIndex(0)

    def toggle_fullscreen_ui(self):
        if self.isFullScreen():
            self.showMaximized()
            self.btn_fullscreen.setText("TOÀN MÀN HÌNH")
        else:
            self.showFullScreen()
            self.btn_fullscreen.setText("THU NHỎ CỬA SỔ")

    def minimize_control_bar(self):
        self.ctrl_bar.hide()
        self.btn_floating_menu.show()
        self.btn_floating_menu.raise_() 

    def restore_control_bar(self):
        self.btn_floating_menu.hide()
        self.ctrl_bar.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self.toggle_fullscreen_ui()
        elif event.key() == Qt.Key_Escape: 
            self.showMaximized()
        super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QWebEngineProfile.defaultProfile().setHttpUserAgent("Mozilla/5.0")
    window = KzKaraoke()
    sys.exit(app.exec_())