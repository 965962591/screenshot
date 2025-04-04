import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QLabel, QSystemTrayIcon, QMenu, QAction, QShortcut
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QScreen, QCursor, QPixmap, QImage, QIcon, QKeySequence
import mss
import numpy as np
from PIL import Image
import subprocess
import win32con
import win32gui
import ctypes
from ctypes import wintypes
from floating_window import create_floating_window

def print_help():
    """打印帮助信息"""
    print("=== 多屏幕截图工具 ===")
    print("操作说明:")
    print("1. 按下 Ctrl+Q 开始截图")
    print("2. 使用鼠标在屏幕上拖动以选择截图区域")
    print("3. 松开鼠标按钮完成截图")
    print("4. 截图将自动保存到 output 文件夹中并复制到剪贴板")
    print("5. 按 ESC 键取消当前截图，程序继续在后台运行")
    print("6. 鼠标移动到不同屏幕自动切换活动屏幕")
    print("7. 按 H 键显示此帮助信息")
    print("8. 按 C 键取消当前选择")
    print("9. 右键点击系统托盘图标可以退出程序")
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
        
        # 检查鼠标是否移动到新的屏幕
        for i, screen in enumerate(self.screens):
            if screen.geometry().contains(cursor_pos):
                if i != self.current_screen_index:
                    # 更新当前屏幕索引
                    old_screen_index = self.current_screen_index
                    self.current_screen_index = i
                    
                    # 打印详细的屏幕切换信息
                    info = self.screen_info[i]
                    if old_screen_index != -1:
                        print(f"鼠标从屏幕 {old_screen_index+1} 移动到屏幕 {i+1}: {info['name']} - {info['size']} 位置: {info['position']}")
                    else:
                        print(f"鼠标移动到屏幕 {i+1}: {info['name']} - {info['size']} 位置: {info['position']}")
                    
                    print(f"鼠标坐标: ({cursor_pos.x()}, {cursor_pos.y()})")
                break

class ScreenOverlay(QWidget):
    def __init__(self, screen_number, screen_geometry, is_active=True):
        super().__init__()
        self.screen_number = screen_number
        self.setGeometry(screen_geometry)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 设置背景透明度
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        
        # 截图区域
        self.begin = QPoint()
        self.end = QPoint()
        self.drawing = False
        
        # 创建提示标签 - 在遮罩的最上层
        self.hint_label = QLabel(self)
        self.hint_label.setText(f"在屏幕 {screen_number+1} 上拖动鼠标选择区域")
        self.hint_label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 150); padding: 10px;")
        
        # 将标签居中显示在屏幕顶部
        self.hint_label.adjustSize()
        self.hint_label.move(screen_geometry.width() // 2 - self.hint_label.width() // 2, 50)
        
        # 确保标签始终在最上层
        self.hint_label.raise_()
        
        # 添加快捷键提示
        self.keys_label = QLabel(self)
        self.keys_label.setText("ESC: 退出截图 | H: 帮助 | C: 取消选择")
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
        
        # 存储父应用的引用，以便截图完成后断开信号连接
        self.parent_app = None
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QWidget) and widget.__class__.__name__ == "ScreenCaptureApp":
                self.parent_app = widget
                break
        
        self.showFullScreen()
    
    def update_mouse_coords(self):
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        screen_geo = QApplication.screens()[self.screen_number].geometry()
        global_x = mouse_pos.x() + screen_geo.left()
        global_y = mouse_pos.y() + screen_geo.top()
        self.coords_label.setText(f"屏幕坐标: ({mouse_pos.x()}, {mouse_pos.y()}) | 全局坐标: ({global_x}, {global_y})")
        self.coords_label.adjustSize()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 绘制半透明背景
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
            
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
            # 正常的绘制逻辑 - 可以在整个窗口任意位置开始绘制
            self.begin = event.pos()
            self.end = event.pos()
            self.drawing = True
            self.update()
            print(f"开始截图选区: 起点({event.pos().x()}, {event.pos().y()})")
    
    def mouseMoveEvent(self, event):
        # 更新鼠标坐标显示，无论是否在绘制
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
            print("取消截图，返回后台等待")
            # 不需要在这里断开连接，因为会调用closeEvent
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
        
        # 如果选区太小，不进行截图
        if selected_rect.width() < 10 or selected_rect.height() < 10:
            print("选择的区域太小，请重新选择 (至少 10x10 像素)")
            return
        
        # 检查是否是浮动截图模式
        if hasattr(self.parent_app, 'is_floating') and self.parent_app.is_floating:
            self.parent_app.capture_floating_screenshot(selected_rect, screen_info)
            self.parent_app.is_floating = False  # 重置浮动标记
            return
        
        # 原有的普通截图逻辑
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
        
        # 关闭所有窗口，返回后台等待状态
        print("截图完成，返回后台等待")
        
        # 不需要在这里断开连接，closeEvent会处理
        
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, ScreenOverlay):
                widget.close()
    
    def closeEvent(self, event):
        # 确保在窗口关闭时断开信号连接并更新父应用状态
        if self.parent_app:
            try:
                # 检查是否是在屏幕切换过程中被关闭的
                is_switching_screens = False
                
                # 获取当前鼠标位置
                cursor_pos = QCursor.pos()
                
                # 如果鼠标位置不在当前屏幕内，可能是在切换屏幕
                for i, screen in enumerate(QApplication.screens()):
                    if (screen.geometry().contains(cursor_pos) and
                        i != self.screen_number and
                        self.parent_app.active_screen_index != -1):
                        is_switching_screens = True
                        print(f"检测到屏幕切换：从屏幕 {self.screen_number+1} 到屏幕 {i+1}")
                        break
                
                # 从overlays列表中删除自己
                if self in self.parent_app.overlays:
                    self.parent_app.overlays.remove(self)
                    print(f"从overlays列表中移除窗口, 剩余: {len(self.parent_app.overlays)}")
                
                # 仅在不是屏幕切换时才断开连接和重置状态
                if not is_switching_screens:
                    print(f"窗口完全关闭，断开信号连接")
                    # 断开信号连接
                    try:
                        self.parent_app.mouse_tracker.timer.timeout.disconnect(self.parent_app.update_active_screen)
                        print("已断开鼠标跟踪器与update_active_screen的连接")
                    except TypeError:
                        print("无法断开信号: 可能没有连接")
                    
                    # 重置父应用状态
                    print(f"重置ScreenCaptureApp状态: active_screen_index={self.parent_app.active_screen_index}->{-1}")
                    self.parent_app.active_screen_index = -1
                    self.parent_app.current_overlay = None
                else:
                    # 如果是屏幕切换，只在日志中记录，不执行断开连接操作
                    print(f"屏幕切换过程中，保持信号连接状态")
                
            except (TypeError, ValueError) as e:
                # 如果连接不存在或移除失败，忽略错误
                print(f"关闭窗口时发生错误: {e}")
                pass
        event.accept()  # 接受关闭事件

# 定义全局热键ID
HOTKEY_ID = 1
FLOATING_HOTKEY_ID = 2  # 新增的热键ID

# 为WM_HOTKEY消息设置窗口消息过滤器
class WinEventFilter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.winId()  # 确保窗口句柄已创建
    
    def nativeEvent(self, eventType, message):
        msg = ctypes.wintypes.MSG.from_address(int(message))
        if msg.message == win32con.WM_HOTKEY:
            if msg.wParam == HOTKEY_ID:
                # 确保在开始新截图前重置状态
                self.parent.reset_screenshot_state()
                self.parent.start_screenshot()
                return True, 0
            elif msg.wParam == FLOATING_HOTKEY_ID:  # 新增的热键ID处理
                self.parent.reset_screenshot_state()
                self.parent.start_floating_screenshot()
                return True, 0
        return False, 0

class ScreenCaptureApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("屏幕截图工具")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # 初始化UI
        self.init_ui()
        
        # 打印帮助信息
        print_help()
        
        self.app = QApplication.instance()
        self.overlays = []
        
        # 创建鼠标跟踪器
        self.mouse_tracker = MouseTracker()
        # 不再将鼠标跟踪器的timeout事件连接到update_active_screen
        # self.mouse_tracker.timer.timeout.connect(self.update_active_screen)
        self.mouse_tracker.show()
        
        # 检测所有屏幕
        self.screens = QApplication.screens()
        
        print(f"检测到 {len(self.screens)} 个显示器")
        
        # 初始状态下没有活动屏幕
        self.active_screen_index = -1
        self.current_overlay = None
        
        # 创建事件过滤器
        self.event_filter = WinEventFilter(self)
        
        # 注册全局热键
        self.register_hotkey()
        
        # 隐藏主窗口
        self.hide()
        
        self.is_floating = False  # 添加浮动截图模式标记
        self.floating_window = None  # 添加浮动窗口引用
    
    def init_ui(self):
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.get_default_icon()))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 添加截图动作
        screenshot_action = QAction("截图 (Ctrl+Q)", self)
        screenshot_action.triggered.connect(self.start_screenshot)
        tray_menu.addAction(screenshot_action)
        
        # 添加帮助动作
        help_action = QAction("帮助", self)
        help_action.triggered.connect(print_help)
        tray_menu.addAction(help_action)
        
        # 添加退出动作
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(exit_action)
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("屏幕截图工具 (Ctrl+Q)")
        
        # 显示托盘图标
        self.tray_icon.show()
        
        # 连接托盘图标的激活信号
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def get_default_icon(self):
        # 如果没有自定义图标，创建一个默认的QPixmap作为图标
        icon = QPixmap(16, 16)
        icon.fill(Qt.transparent)
        painter = QPainter(icon)
        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(QColor(0, 120, 215))
        painter.drawRect(2, 2, 12, 12)
        painter.end()
        return icon
    
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.start_screenshot()
    
    def register_hotkey(self):
        # 注册Ctrl+Q全局热键
        self.event_filter.show()
        self.event_filter.hide()  # 隐藏但保持活动状态
        
        # 注册全局热键
        hwnd = int(self.event_filter.winId())
        if not win32gui.RegisterHotKey(hwnd, HOTKEY_ID, win32con.MOD_CONTROL, ord('Q')):
            print("注册全局热键Ctrl+Q失败")
        else:
            print("已注册全局热键: Ctrl+Q (用于开始截图)")
        
        # 注册Ctrl+W全局热键
        if not win32gui.RegisterHotKey(hwnd, FLOATING_HOTKEY_ID, win32con.MOD_CONTROL, ord('W')):
            print("注册全局热键Ctrl+W失败")
        else:
            print("已注册全局热键: Ctrl+W (用于浮动截图)")
    
    def update_active_screen(self):
        # 此方法仅在已经开始截图时使用，用于在截图过程中切换屏幕
        if self.current_overlay is not None:
            # 获取当前鼠标位置
            cursor_pos = QCursor.pos()
            # 查找鼠标所在的屏幕
            for i, screen in enumerate(self.screens):
                if screen.geometry().contains(cursor_pos):
                    # 如果鼠标移动到了不同的屏幕，更新遮罩
                    if i != self.active_screen_index:
                        print(f"鼠标移动到屏幕 {i+1}, 切换活动屏幕 {self.active_screen_index+1}->{i+1}")
                        
                        # 先保存当前屏幕索引
                        old_screen_index = self.active_screen_index
                        
                        # 更新屏幕索引，确保在关闭旧窗口前已更新
                        self.active_screen_index = i
                        
                        # 关闭当前遮罩
                        if self.current_overlay:
                            print(f"关闭屏幕 {old_screen_index+1} 的遮罩")
                            old_overlay = self.current_overlay
                            self.current_overlay = None  # 先置空，避免引用问题
                            old_overlay.close()
                            # 不需要在这里移除，closeEvent会处理
                        
                        # 强制处理事件，确保旧窗口完全关闭
                        QApplication.processEvents()
                        
                        # 为新的屏幕创建遮罩
                        geometry = screen.geometry()
                        print(f"创建屏幕 {i+1} 的新遮罩")
                        self.current_overlay = ScreenOverlay(i, geometry, True)
                        self.overlays.append(self.current_overlay)
                        
                        # 确保窗口显示并处于最前端
                        self.current_overlay.showFullScreen()
                        self.current_overlay.raise_()  # 提升窗口Z顺序到最前
                        self.current_overlay.activateWindow()  # 提高窗口优先级
                        
                        # 强制重绘窗口
                        self.current_overlay.update()
                        
                        # 强制处理一次事件
                        QApplication.processEvents()
                        
                        print(f"激活屏幕 {i+1} 用于截图 - 鼠标位置: ({cursor_pos.x()}, {cursor_pos.y()})")
                    break
    
    def reset_screenshot_state(self):
        """重置所有截图相关状态，强制清理所有资源"""
        print("强制重置截图状态...")
        
        # 断开鼠标跟踪器信号（如果已连接）
        try:
            # 正确的disconnect方法用法：
            self.mouse_tracker.timer.timeout.disconnect(self.update_active_screen)
            print("已断开鼠标跟踪器与update_active_screen的连接")
        except TypeError:
            print("没有活动的鼠标跟踪器连接")
        
        # 关闭所有活动的截图窗口
        overlays_to_close = []
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, ScreenOverlay):
                overlays_to_close.append(widget)
        
        # 先复制列表再关闭窗口，避免迭代过程中列表变化
        for overlay in overlays_to_close:
            print(f"关闭遗留的截图窗口: 屏幕 {overlay.screen_number+1}")
            overlay.close()
        
        # 关闭任何存在的浮动窗口
        if hasattr(self, 'floating_window') and self.floating_window is not None:
            try:
                print("关闭遗留的浮动窗口")
                self.floating_window.close()
                self.floating_window = None
            except Exception as e:
                print(f"关闭浮动窗口时出错: {e}")
        
        # 重置浮动截图模式
        self.is_floating = False
        
        # 重置状态变量
        self.active_screen_index = -1
        self.current_overlay = None
        self.overlays = []
        print("截图状态已重置")
    
    def start_screenshot(self):
        print("开始截图操作...")
        
        # 检查是否已经有活动的截图会话
        if self.current_overlay is not None:
            print(f"已有截图会话在进行中，active_screen_index={self.active_screen_index+1}, overlays数量={len(self.overlays)}")
            # 强制重置状态以确保能够开始新的截图
            self.reset_screenshot_state()
            
        # 确保处理所有待处理事件，防止出现在重置状态后仍有窗口未关闭的情况
        QApplication.processEvents()
        
        # 获取当前鼠标位置
        cursor_pos = QCursor.pos()
        
        # 查找鼠标所在的屏幕
        for i, screen in enumerate(self.screens):
            if screen.geometry().contains(cursor_pos):
                self.active_screen_index = i
                print(f"鼠标当前在屏幕 {i+1} 上，位置: ({cursor_pos.x()}, {cursor_pos.y()})")
                
                # 创建并显示遮罩
                geometry = screen.geometry()
                print(f"创建屏幕 {i+1} 的遮罩: 位置({geometry.left()}, {geometry.top()}), 大小({geometry.width()}x{geometry.height()})")
                self.current_overlay = ScreenOverlay(i, geometry, True)
                self.overlays.append(self.current_overlay)
                
                # 确保窗口显示并处于最前端
                self.current_overlay.showFullScreen()
                self.current_overlay.raise_()
                self.current_overlay.activateWindow()
                
                # 强制重绘和处理事件
                self.current_overlay.update()
                QApplication.processEvents()
                
                print(f"当前活动窗口数量: {len(self.overlays)}")
                
                # 开始截图后，连接鼠标跟踪器信号以允许在不同屏幕间切换
                try:
                    # 先尝试断开以防止重复连接
                    print("尝试断开已有的信号连接...")
                    # 正确的disconnect方法用法：
                    self.mouse_tracker.timer.timeout.disconnect(self.update_active_screen)
                except TypeError:
                    print("没有已存在的信号连接")
                    pass  # 如果没有连接，忽略错误
                    
                # 连接信号
                print("连接鼠标跟踪器与update_active_screen")
                self.mouse_tracker.timer.timeout.connect(self.update_active_screen)
                break
        
        # 如果没有找到屏幕
        if self.current_overlay is None:
            print("未能找到鼠标所在的屏幕，截图操作取消")
    
    def start_floating_screenshot(self):
        """开始浮动截图操作"""
        print("开始浮动截图操作...")
        self.is_floating = True  # 标记为浮动截图模式
        self.start_screenshot()

    def capture_floating_screenshot(self, selected_rect, screen_info):
        """执行浮动截图"""
        try:
            print("开始执行浮动截图...")
            # 隐藏所有窗口以便截图
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, ScreenOverlay):
                    widget.hide()
            QApplication.processEvents()
            
            # 使用mss进行截图
            with mss.mss() as sct:
                # 计算截图区域
                monitor = {
                    "left": selected_rect.left() + screen_info.left(),
                    "top": selected_rect.top() + screen_info.top(),
                    "width": selected_rect.width(),
                    "height": selected_rect.height()
                }
                
                print(f"截图区域: 左上角({monitor['left']}, {monitor['top']}), 宽x高({monitor['width']}x{monitor['height']})")
                
                try:
                    # 抓取屏幕
                    screenshot = sct.grab(monitor)
                    
                    # 确保截图数据有效
                    if screenshot.size[0] <= 0 or screenshot.size[1] <= 0:
                        print(f"截图大小无效: {screenshot.size}")
                        return
                    
                    print(f"成功抓取屏幕，图像大小: {screenshot.size[0]}x{screenshot.size[1]}")
                    
                    try:
                        # 转换截图为PIL图像
                        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                        
                        # 临时保存文件，确保图像数据正确
                        if not os.path.exists("output"):
                            os.makedirs("output")
                        
                        # 生成临时文件名
                        import datetime
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        temp_filename = f"output/floating_{timestamp}.png"
                        img.save(temp_filename)
                        print(f"临时文件已保存: {temp_filename}")
                        
                        # 使用保存的文件创建QPixmap (更可靠的方法)
                        pixmap = QPixmap(temp_filename)
                        
                        # 如果直接从文件创建失败，尝试使用QImage作为中介
                        if pixmap.isNull():
                            print("使用临时文件创建QPixmap失败，尝试使用QImage...")
                            # 从保存的文件加载QImage
                            qimg = QImage(temp_filename)
                            if not qimg.isNull():
                                pixmap = QPixmap.fromImage(qimg)
                        
                        # 如果pixmap创建成功且有效
                        if not pixmap.isNull() and pixmap.width() > 0 and pixmap.height() > 0:
                            print(f"创建有效的QPixmap: {pixmap.width()}x{pixmap.height()}")
                            # 创建浮动窗口
                            self.floating_window = create_floating_window(pixmap=pixmap)
                            print("成功创建悬浮窗口")
                        else:
                            print(f"无法创建有效的QPixmap，大小: {pixmap.width()}x{pixmap.height()}")
                    except Exception as e:
                        print(f"图像转换或创建QPixmap过程中出错: {e}")
                except Exception as e:
                    print(f"截图过程中出错: {e}")
        except Exception as e:
            print(f"浮动截图操作失败: {e}")
        finally:
            # 确保关闭所有遮罩窗口，即使过程中发生异常
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, ScreenOverlay):
                    widget.close()
            
            # 如果浮动窗口创建失败，确保重置浮动模式标志
            if self.floating_window is None:
                print("浮动窗口创建失败，重置浮动模式标志")
                self.is_floating = False
            
            print("浮动截图操作完成")

    def quit_app(self):
        print("退出程序")
        # 注销全局热键
        try:
            hwnd = int(self.event_filter.winId())
            win32gui.UnregisterHotKey(hwnd, HOTKEY_ID)
            win32gui.UnregisterHotKey(hwnd, FLOATING_HOTKEY_ID)  # 注销Ctrl+W热键
        except:
            pass
        
        # 关闭所有窗口
        for widget in QApplication.topLevelWidgets():
            widget.close()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    screen_capture_app = ScreenCaptureApp()
    sys.exit(app.exec_())
