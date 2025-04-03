import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QLabel
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QScreen, QCursor, QPixmap, QImage
import mss
import numpy as np
from PIL import Image
import subprocess

def print_help():
    """打印帮助信息"""
    print("=== 多屏幕截图工具 ===")
    print("操作说明:")
    print("1. 使用鼠标在任意屏幕上拖动以选择截图区域")
    print("2. 松开鼠标按钮完成截图")
    print("3. 截图将自动保存到 output 文件夹中并复制到剪贴板")
    print("4. 按 ESC 键退出程序")
    print("5. 鼠标移动到不同屏幕自动切换活动屏幕")
    print("6. 也可以点击非活动屏幕上的遮罩来激活该屏幕")
    print("7. 按 H 键显示此帮助信息")
    print("8. 按 C 键取消当前选择")
    print("====================")

class MouseTracker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 设置零大小窗口，但仍然可以跟踪鼠标
        self.setGeometry(0, 0, 1, 1)
        
        # 当前鼠标所在屏幕的索引
        self.current_screen_index = -1
        
        # 设置定时器检测鼠标位置
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_mouse_position)
        self.timer.start(100)  # 每100毫秒检查一次
        
        self.screens = QApplication.screens()
        self.screen_info = []
        
        # 收集所有屏幕信息
        for i, screen in enumerate(self.screens):
            geo = screen.geometry()
            self.screen_info.append({
                "index": i,
                "name": screen.name(),
                "geometry": geo,
                "size": f"{geo.width()}x{geo.height()}",
                "position": f"({geo.left()},{geo.top()})"
            })
            print(f"检测到屏幕 {i+1}: {screen.name()} - 分辨率: {geo.width()}x{geo.height()} 位置: ({geo.left()},{geo.top()})")
    
    def check_mouse_position(self):
        cursor_pos = QCursor.pos()
        for i, screen in enumerate(self.screens):
            if screen.geometry().contains(cursor_pos):
                if i != self.current_screen_index:
                    self.current_screen_index = i
                    info = self.screen_info[i]
                    print(f"鼠标移动到屏幕 {i+1}: {info['name']} - 分辨率: {info['size']} 位置: {info['position']}")
                    print(f"鼠标坐标: ({cursor_pos.x()}, {cursor_pos.y()})")
                break

class ScreenOverlay(QWidget):
    def __init__(self, screen_number, screen_geometry, is_active=False):
        super().__init__()
        self.screen_number = screen_number
        self.setGeometry(screen_geometry)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 根据是否是活动屏幕设置不同的背景透明度
        self.is_active = is_active
        if is_active:
            self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        else:
            self.setStyleSheet("background-color: rgba(0, 0, 0, 150);")
        
        # 截图区域
        self.begin = QPoint()
        self.end = QPoint()
        self.drawing = False
        
        # 创建提示标签 - 在遮罩的最上层
        self.hint_label = QLabel(self)
        if is_active:
            self.hint_label.setText(f"在屏幕 {screen_number+1} 上拖动鼠标选择区域")
            self.hint_label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 150); padding: 10px;")
        else:
            self.hint_label.setText(f"点击此屏幕 {screen_number+1} 进行截图")
            self.hint_label.setStyleSheet("color: #CCCCCC; background-color: rgba(0, 0, 0, 170); padding: 10px;")
        
        # 将标签居中显示在屏幕顶部
        self.hint_label.adjustSize()
        self.hint_label.move(screen_geometry.width() // 2 - self.hint_label.width() // 2, 50)
        
        # 确保标签始终在最上层
        self.hint_label.raise_()
        
        # 添加快捷键提示
        self.keys_label = QLabel(self)
        self.keys_label.setText("ESC: 退出 | H: 帮助 | C: 取消选择")
        self.keys_label.setStyleSheet("color: #AAAAAA; background-color: rgba(0, 0, 0, 150); padding: 5px;")
        self.keys_label.move(screen_geometry.width() - 250, screen_geometry.height() - 30)
        self.keys_label.adjustSize()
        self.keys_label.raise_()  # 确保在最上层
        
        # 添加鼠标坐标显示
        self.coords_label = QLabel(self)
        self.coords_label.setStyleSheet("color: #AAAAAA; background-color: rgba(0, 0, 0, 150); padding: 5px;")
        self.coords_label.move(10, screen_geometry.height() - 30)
        self.coords_label.adjustSize()
        self.coords_label.raise_()  # 确保在最上层
        
        # 定时器用于更新鼠标坐标
        self.coord_timer = QTimer(self)
        self.coord_timer.timeout.connect(self.update_mouse_coords)
        self.coord_timer.start(50)  # 每50毫秒更新一次
        
        # 设置widget接受鼠标事件
        self.setMouseTracking(True)
        
        self.showFullScreen()

    def update_mouse_coords(self):
        if self.is_active:
            mouse_pos = self.mapFromGlobal(QCursor.pos())
            screen_geo = QApplication.screens()[self.screen_number].geometry()
            global_x = mouse_pos.x() + screen_geo.left()
            global_y = mouse_pos.y() + screen_geo.top()
            self.coords_label.setText(f"屏幕坐标: ({mouse_pos.x()}, {mouse_pos.y()}) | 全局坐标: ({global_x}, {global_y})")
            self.coords_label.adjustSize()

    def set_active(self, active):
        self.is_active = active
        if active:
            self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
            self.hint_label.setText(f"在屏幕 {self.screen_number+1} 上拖动鼠标选择区域")
            self.hint_label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 150); padding: 10px;")
        else:
            self.setStyleSheet("background-color: rgba(0, 0, 0, 150);")
            self.hint_label.setText(f"点击此屏幕 {self.screen_number+1} 进行截图")
            self.hint_label.setStyleSheet("color: #CCCCCC; background-color: rgba(0, 0, 0, 170); padding: 10px;")
        self.hint_label.adjustSize()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 绘制半透明背景
        if self.is_active:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 150))
            
        # 如果正在绘制选择框
        if self.drawing and not self.begin.isNull() and not self.end.isNull():
            # 绘制选定区域 (透明)
            selected_rect = QRect(self.begin, self.end).normalized()
            painter.fillRect(selected_rect, QColor(255, 255, 255, 0))
            
            # 绘制选定区域边框
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)
            painter.drawRect(selected_rect)
            
            # 显示尺寸信息
            size_text = f"{selected_rect.width()} x {selected_rect.height()}"
            text_x = selected_rect.x() + selected_rect.width() + 5
            text_y = selected_rect.y() + 20
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(text_x, text_y, size_text)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 如果当前屏幕不是活动的，通知应用程序激活此屏幕
            if not self.is_active:
                # 发射自定义事件或信号，这里使用全局变量应用程序实例来访问
                app = QApplication.instance()
                for widget in app.topLevelWidgets():
                    if isinstance(widget, ScreenOverlay) and widget.is_active:
                        widget.set_active(False)
                
                self.set_active(True)
                print(f"用户点击了屏幕 {self.screen_number+1}，现在激活此屏幕用于截图")
                return
            
            # 正常的绘制逻辑 - 可以在整个窗口任意位置开始绘制
            self.begin = event.pos()
            self.end = event.pos()
            self.drawing = True
            self.update()
            print(f"开始截图选区: 起点({event.pos().x()}, {event.pos().y()})")
    
    def mouseMoveEvent(self, event):
        # 更新鼠标坐标显示，无论是否在绘制
        if self.is_active:
            # 如果正在绘制，更新选区
            if self.drawing:
                self.end = event.pos()
                self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.end = event.pos()
            self.drawing = False
            selected_rect = QRect(self.begin, self.end).normalized()
            print(f"完成截图选区: 终点({event.pos().x()}, {event.pos().y()}), 大小: {selected_rect.width()}x{selected_rect.height()}")
            
            # 更新显示
            self.update()
            
            # 如果选区太小，不进行截图
            if selected_rect.width() < 10 or selected_rect.height() < 10:
                print("选择的区域太小，请重新选择 (至少 10x10 像素)")
                return
                
            # 执行截图
            self.capture_screenshot()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_H:
            print_help()
        elif event.key() == Qt.Key_C and self.drawing:
            # 取消当前的选择
            self.drawing = False
            self.begin = QPoint()
            self.end = QPoint()
            self.update()
            print("已取消当前选择")
            
    def capture_screenshot(self):
        selected_rect = QRect(self.begin, self.end).normalized()
        
        # 计算相对于屏幕的坐标
        screen_info = QApplication.screens()[self.screen_number].geometry()
        left = selected_rect.left() + screen_info.left()
        top = selected_rect.top() + screen_info.top()
        width = selected_rect.width()
        height = selected_rect.height()
        
        # 隐藏所有窗口以便截图
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, ScreenOverlay):
                widget.hide()
        QApplication.processEvents()
        
        # 使用mss进行截图
        with mss.mss() as sct:
            monitor = {
                "left": left,
                "top": top,
                "width": width,
                "height": height
            }
            screenshot = sct.grab(monitor)
            
            # 保存截图
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            
            # 确保输出目录存在
            if not os.path.exists("output"):
                os.makedirs("output")
            
            # 生成文件名
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"output/screenshot_{timestamp}.png"
            img.save(filename)
            
            print(f"截图已保存: {filename}")
            print(f"截图区域: 左上角({left}, {top}), 宽x高({width}x{height})")
            
            # 将截图复制到剪贴板
            try:
                # 转换为QPixmap然后放入剪贴板
                q_img = QImage(filename)
                pixmap = QPixmap.fromImage(q_img)
                QApplication.clipboard().setPixmap(pixmap)
                print("截图已复制到剪贴板")
            except Exception as e:
                print(f"复制到剪贴板失败: {e}")
        
        # 关闭所有窗口
        for widget in QApplication.topLevelWidgets():
            widget.close()

class ScreenCaptureApp:
    def __init__(self):
        # 打印帮助信息
        print_help()
        
        self.app = QApplication(sys.argv)
        self.overlays = []
        
        # 创建鼠标跟踪器
        self.mouse_tracker = MouseTracker()
        # 设置鼠标跟踪器的回调，以便在鼠标移动到不同屏幕时更新遮罩状态
        self.mouse_tracker.timer.timeout.connect(self.update_active_screen)
        self.mouse_tracker.show()
        
        # 检测所有屏幕
        self.screens = QApplication.screens()
        
        print(f"检测到 {len(self.screens)} 个显示器")
        
        # 检测鼠标当前所在的屏幕
        cursor_pos = QCursor.pos()
        self.active_screen_index = 0
        
        for i, screen in enumerate(self.screens):
            geometry = screen.geometry()
            if geometry.contains(cursor_pos):
                self.active_screen_index = i
                print(f"鼠标当前在屏幕 {i+1} 上，位置: ({cursor_pos.x()}, {cursor_pos.y()})")
                break
        
        # 为每个屏幕创建遮罩
        for i, screen in enumerate(self.screens):
            geometry = screen.geometry()
            print(f"创建屏幕 {i+1} 的遮罩: 位置({geometry.left()}, {geometry.top()}), 大小({geometry.width()}x{geometry.height()})")
            overlay = ScreenOverlay(i, geometry, i == self.active_screen_index)
            self.overlays.append(overlay)
    
    def update_active_screen(self):
        # 获取当前鼠标位置
        cursor_pos = QCursor.pos()
        # 查找鼠标所在的屏幕
        for i, screen in enumerate(self.screens):
            if screen.geometry().contains(cursor_pos):
                # 如果鼠标移动到了不同的屏幕，更新活动遮罩
                if i != self.active_screen_index:
                    # 将之前的活动屏幕设为非活动
                    self.overlays[self.active_screen_index].set_active(False)
                    # 将当前屏幕设为活动
                    self.overlays[i].set_active(True)
                    self.active_screen_index = i
                    print(f"激活屏幕 {i+1} 用于截图 - 鼠标位置: ({cursor_pos.x()}, {cursor_pos.y()})")
                break
    
    def run(self):
        return self.app.exec_()

if __name__ == "__main__":
    app = ScreenCaptureApp()
    sys.exit(app.run())
