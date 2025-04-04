from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import os
import sys
import math
import datetime

class ScreenshotEditor(QWidget):
    """用于编辑截图的窗口，提供各种编辑工具"""
    
    # 定义一个信号，用于通知截图编辑完成
    editingFinished = pyqtSignal(QPixmap)
    
    def __init__(self, pixmap=None, screen_pos=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 保存原始图像和当前编辑的图像
        self.original_pixmap = pixmap
        
        # 编辑时添加蓝色边框
        self.current_pixmap = self.addBorderToPixmap(pixmap) if pixmap else QPixmap(800, 600)
        
        # 编辑状态
        self.is_drawing = False
        self.current_tool = None  # 当前选中的工具
        self.start_point = QPoint()
        self.end_point = QPoint()
        
        # 画笔设置
        self.pen_color = QColor(255, 0, 0)  # 默认红色
        self.pen_width = 2
        self.text_font = QFont("SimSun", 12)  # 使用宋体作为默认字体支持中文
        self.mosaic_size = 10  # 马赛克大小
        self.text_bold = False  # 是否使用粗体
        
        # 绘制的对象
        self.shapes = []  # 存储所有绘制的形状
        self.temp_text = ""  # 临时存储文本
        
        # 文本输入相关属性
        self.is_text_input = False  # 是否在输入文本
        self.current_text = ""  # 当前正在输入的文本
        self.text_cursor_pos = 0  # 文本光标位置
        self.text_cursor_visible = True  # 文本光标是否可见
        self.text_cursor_timer = None  # 文本光标闪烁定时器
        
        # 标记移动相关属性
        self.is_moving_shape = False  # 是否正在移动形状
        self.moving_shape_index = -1  # 当前移动的形状索引
        self.move_start_pos = QPoint()  # 移动开始位置
        
        # 调整大小相关属性
        self.is_resizing = False  # 是否正在调整大小
        self.resize_shape_index = -1  # 当前调整大小的形状索引
        self.resize_handle = -1  # 当前调整的控制点，0-左上，1-右上，2-左下，3-右下
        
        # 启用输入法支持
        self.setAttribute(Qt.WA_InputMethodEnabled, True)
        
        # 属性面板状态
        self.property_panel_visible = False
        self.property_panel = None
        
        # 保存屏幕位置
        self.screen_pos = screen_pos
        
        self.initUI()
    
    def initUI(self):
        # 创建布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 设置窗口和布局为透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建图像显示区域
        self.image_label = QLabel()
        self.image_label.setPixmap(self.current_pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMouseTracking(True)
        self.image_label.installEventFilter(self)
        
        # 设置图像标签的尺寸策略，确保图像不会被拉伸
        self.image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.image_label.setScaledContents(False)
        # 设置图像标签的背景为透明
        self.image_label.setStyleSheet("background-color: transparent;")
        
        # 创建一个容器部件，包含工具栏等控件
        self.controls_container = QWidget()
        self.controls_container.setStyleSheet("background-color: #3D3D3D;")
        controls_layout = QVBoxLayout(self.controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(0)
        
        # 创建工具栏
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(32, 32))
        # 设置工具栏可以自适应大小，并添加滚动条
        self.toolbar.setMovable(False)  # 禁止移动工具栏
        self.toolbar.setFloatable(False)  # 禁止浮动
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #3D3D3D;
                border: none;
                spacing: 2px;
                padding: 5px;
                min-height: 45px;
            }
            QToolBar::separator {
                background-color: #5A5A5A;
                width: 1px;
                margin: 0px 5px;
            }
            QToolButton {
                border: none;
                border-radius: 4px;
                background-color: transparent;
                padding: 5px;
                color: white;
                min-width: 40px;
            }
            QToolButton:hover {
                background-color: #505050;
            }
            QToolButton:pressed {
                background-color: #707070;
            }
            QToolButton:checked {
                background-color: #505050;
            }
        """)
        
        # 添加工具按钮
        self.addToolbarButtons()
        
        # 创建属性面板（初始隐藏）
        self.property_panel = QWidget()
        self.property_panel.setStyleSheet("""
            QWidget {
                background-color: #3D3D3D;
                color: white;
                border: none;
            }
            QLabel {
                color: white;
            }
            QSlider {
                height: 20px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #4D4D4D;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #CCCCCC;
                border: 1px solid #5C5C5C;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #5A5A5A;
                border: none;
                border-radius: 3px;
                padding: 5px;
                color: white;
            }
            QPushButton:hover {
                background-color: #6A6A6A;
            }
            QPushButton:pressed {
                background-color: #7A7A7A;
            }
            QComboBox {
                background-color: #5A5A5A;
                border: none;
                border-radius: 3px;
                padding: 5px;
                color: white;
            }
            QComboBox::drop-down {
                border-color: transparent;
            }
            QCheckBox {
                color: white;
            }
        """)
        self.property_panel.setFixedHeight(50)
        self.property_panel.hide()
        
        # 准备属性面板布局
        self.property_layout = QHBoxLayout(self.property_panel)
        self.property_layout.setContentsMargins(10, 5, 10, 5)
        
        # 将组件添加到布局
        controls_layout.addWidget(self.property_panel)
        controls_layout.addWidget(self.toolbar)
        
        # 获取工具栏预期尺寸
        self.toolbar.adjustSize()
        toolbar_width = self.toolbar.sizeHint().width()
        toolbar_height = self.toolbar.sizeHint().height()
        if self.property_panel.isVisible():
            toolbar_height += self.property_panel.height()
        
        # 默认布局 - 工具栏在底部
        main_layout.addWidget(self.image_label)
        main_layout.addWidget(self.controls_container)
        
        self.setLayout(main_layout)
        
        # 设置窗口大小
        min_width = max(600, toolbar_width + 20)  # 设置最小宽度，确保工具栏能完整显示
        
        if self.current_pixmap:
            # 确保窗口宽度不小于最小宽度
            window_width = max(self.current_pixmap.width(), min_width)
            window_height = self.current_pixmap.height() + toolbar_height + 10
            self.resize(window_width, window_height)
        else:
            self.resize(800, 650)
            
        # 设置窗口最小尺寸
        self.setMinimumWidth(min_width)
        
        # 启用输入法
        self.setAttribute(Qt.WA_InputMethodEnabled, True)
        
        # 确保图像已添加边框
        if self.original_pixmap and self.current_pixmap.width() == self.original_pixmap.width():
            # 如果当前图像没有边框，添加边框
            self.current_pixmap = self.addBorderToPixmap(self.original_pixmap)
        
        self.updateImageLabel()
        
        # 移动窗口到指定位置，并调整位置确保工具栏完全可见
        if self.screen_pos:
            self.adjustWindowPosition()
        
        self.show()
        
        # 窗口显示后，确保工具栏完全可见
        QTimer.singleShot(100, self.ensureToolbarVisible)
        
    def adjustWindowPosition(self):
        """根据屏幕位置调整窗口位置，确保工具栏完全可见"""
        if not self.screen_pos:
            return
            
        # 获取当前屏幕信息
        screen = QApplication.screenAt(self.screen_pos)
        if not screen:
            screen = QApplication.primaryScreen()
        
        screen_geometry = screen.availableGeometry()
        
        # 获取窗口和工具栏尺寸
        window_width = self.width()
        window_height = self.height()
        toolbar_height = self.controls_container.sizeHint().height()
        
        # 计算窗口右下角坐标
        bottom_right_x = self.screen_pos.x() + window_width
        bottom_right_y = self.screen_pos.y() + window_height
        
        # 检查是否需要调整窗口位置
        adjusted_pos = QPoint(self.screen_pos)
        
        # 检查右边界
        if bottom_right_x > screen_geometry.right():
            # 窗口右侧超出屏幕，向左移动
            adjusted_pos.setX(max(screen_geometry.left(), screen_geometry.right() - window_width))
        
        # 检查底部边界
        if bottom_right_y > screen_geometry.bottom():
            # 窗口底部超出屏幕，向上移动
            adjusted_pos.setY(max(screen_geometry.top(), screen_geometry.bottom() - window_height))
        
        # 应用调整后的位置
        self.move(adjusted_pos)
        
        # 记录调整后的位置，用于后续计算
        self.screen_pos = adjusted_pos
        
    def ensureToolbarVisible(self):
        """确保工具栏完全可见，如果需要则改变布局"""
        if not hasattr(self, 'screen_pos') or not self.screen_pos:
            return
            
        # 获取当前屏幕信息
        screen = QApplication.screenAt(self.mapToGlobal(QPoint(0, 0)))
        if not screen:
            screen = QApplication.primaryScreen()
            
        screen_geometry = screen.availableGeometry()
        
        # 获取窗口位置和尺寸
        window_pos = self.mapToGlobal(QPoint(0, 0))
        window_width = self.width()
        window_height = self.height()
        
        # 获取工具栏尺寸
        toolbar_height = self.controls_container.sizeHint().height()
        toolbar_width = self.controls_container.sizeHint().width()
        
        # 检查工具栏是否会超出屏幕底部
        if window_pos.y() + window_height > screen_geometry.bottom():
            # 将工具栏移到顶部
            main_layout = self.layout()
            main_layout.removeWidget(self.image_label)
            main_layout.removeWidget(self.controls_container)
            
            main_layout.addWidget(self.controls_container)
            main_layout.addWidget(self.image_label)
            
            print("工具栏移到顶部")
        
        # 检查工具栏是否会超出屏幕右侧
        if window_pos.x() + toolbar_width > screen_geometry.right():
            # 设置工具栏右对齐
            self.toolbar.setLayoutDirection(Qt.RightToLeft)
            print("工具栏设置为右对齐")
        else:
            # 设置工具栏左对齐
            self.toolbar.setLayoutDirection(Qt.LeftToRight)
        
        # 强制更新布局
        self.updateGeometry()
    
    def createToolButton(self, text, icon_color, callback, tooltip=None):
        """创建工具按钮"""
        action = QAction(text, self)
        
        # 创建一个彩色图标
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(icon_color)))
        
        # 根据按钮类型绘制不同的图标
        if text == "矩形":
            painter.drawRect(4, 4, 16, 16)
        elif text == "圆形":
            painter.drawEllipse(4, 4, 16, 16)
        elif text == "箭头":
            points = [QPoint(4, 12), QPoint(20, 12), QPoint(16, 8), QPoint(20, 12), QPoint(16, 16)]
            for i in range(len(points) - 1):
                painter.setPen(QPen(QColor(icon_color), 2))
                painter.drawLine(points[i], points[i+1])
        elif text == "直接输入":
            painter.end()
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor(icon_color)))
            painter.setFont(QFont("Arial", 14, QFont.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "I")
        elif text == "马赛克":
            block_size = 4
            for x in range(0, 24, block_size):
                for y in range(0, 24, block_size):
                    if (x // block_size + y // block_size) % 2 == 0:
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(QBrush(QColor(icon_color)))
                        painter.drawRect(x, y, block_size, block_size)
        
        painter.end()
        
        # 设置图标和工具提示
        action.setIcon(QIcon(pixmap))
        if tooltip:
            action.setToolTip(tooltip)
        
        # 连接回调函数
        action.triggered.connect(callback)
        
        return action
    
    def addToolbarButtons(self):
        """添加工具栏按钮"""
        # 绘图工具组
        self.toolbar.addAction(self.createToolButton("矩形", "#FF6B6B", lambda: self.setTool("rectangle"), "矩形工具 - 绘制可移动的矩形"))
        self.toolbar.addAction(self.createToolButton("圆形", "#4ECDC4", lambda: self.setTool("circle"), "圆形工具 - 绘制可移动的圆形或椭圆"))
        self.toolbar.addAction(self.createToolButton("箭头", "#FFE66D", lambda: self.setTool("arrow"), "箭头工具 - 绘制箭头"))
        
        # 添加分隔符
        self.toolbar.addSeparator()
        
        # 标注工具组 - 只保留直接文本输入
        text_input_action = self.createToolButton("直接输入", "#FF9F1C", lambda: self.setTool("text_input"), "直接输入文本 - 在图像上直接键入文字")
        self.toolbar.addAction(text_input_action)
        self.toolbar.addAction(self.createToolButton("马赛克", "#2EC4B6", lambda: self.setTool("mosaic"), "马赛克工具 - 模糊选定区域"))
        
        # 添加分隔符
        self.toolbar.addSeparator()
        
        # 编辑操作组
        undo_action = QAction("撤销", self)
        undo_pixmap = QPixmap(24, 24)
        undo_pixmap.fill(Qt.transparent)
        undo_painter = QPainter(undo_pixmap)
        undo_painter.setPen(QPen(Qt.white, 2))
        undo_painter.drawArc(4, 4, 16, 16, 90 * 16, 270 * 16)
        # 绘制箭头
        undo_painter.drawLine(4, 12, 8, 8)
        undo_painter.drawLine(4, 12, 8, 16)
        undo_painter.end()
        undo_action.setIcon(QIcon(undo_pixmap))
        undo_action.setToolTip("撤销上一步操作")
        undo_action.triggered.connect(self.undo)
        self.toolbar.addAction(undo_action)
        
        # 清除所有
        clear_action = QAction("清除", self)
        clear_pixmap = QPixmap(24, 24)
        clear_pixmap.fill(Qt.transparent)
        clear_painter = QPainter(clear_pixmap)
        clear_painter.setPen(QPen(Qt.white, 2))
        clear_painter.drawLine(4, 4, 20, 20)
        clear_painter.drawLine(4, 20, 20, 4)
        clear_painter.end()
        clear_action.setIcon(QIcon(clear_pixmap))
        clear_action.setToolTip("清除所有编辑")
        clear_action.triggered.connect(self.clearAll)
        self.toolbar.addAction(clear_action)
        
        # 添加复制到剪贴板按钮 - 更加明显
        copy_action = QAction("复制", self)
        copy_pixmap = QPixmap(24, 24)
        copy_pixmap.fill(Qt.transparent)
        copy_painter = QPainter(copy_pixmap)
        # 用更醒目的颜色绘制
        copy_painter.setPen(QPen(QColor(255, 215, 0), 2))  # 金色
        copy_painter.drawRect(8, 4, 12, 12)
        copy_painter.drawRect(4, 8, 12, 12)
        copy_painter.end()
        copy_action.setIcon(QIcon(copy_pixmap))
        copy_action.setToolTip("复制到剪贴板并隐藏")
        copy_action.triggered.connect(self.copyToClipboard)
        self.toolbar.addAction(copy_action)
        
        # 添加分隔符
        self.toolbar.addSeparator()
        
        # 最终操作组
        save_action = QAction("保存", self)
        save_pixmap = QPixmap(24, 24)
        save_pixmap.fill(Qt.transparent)
        save_painter = QPainter(save_pixmap)
        save_painter.setPen(QPen(Qt.white, 2))
        save_painter.drawRect(4, 4, 16, 16)
        save_painter.drawLine(8, 12, 12, 16)
        save_painter.drawLine(12, 16, 16, 12)
        save_painter.end()
        save_action.setIcon(QIcon(save_pixmap))
        save_action.setToolTip("保存到文件并隐藏")
        save_action.triggered.connect(self.saveImage)
        self.toolbar.addAction(save_action)
        
        # 添加关闭按钮 - 隐藏窗口但不关闭程序
        close_action = QAction("关闭", self)
        close_pixmap = QPixmap(24, 24)
        close_pixmap.fill(Qt.transparent)
        close_painter = QPainter(close_pixmap)
        close_painter.setPen(QPen(Qt.white, 2))
        close_painter.drawLine(6, 6, 18, 18)
        close_painter.drawLine(6, 18, 18, 6)
        close_painter.end()
        close_action.setIcon(QIcon(close_pixmap))
        close_action.setToolTip("隐藏界面")
        close_action.triggered.connect(self.hideEditor)
        self.toolbar.addAction(close_action)
    
    def setTool(self, tool_name):
        """设置当前使用的工具"""
        # 如果之前在进行文本输入，取消输入状态
        if self.is_text_input and tool_name != "text_input":
            if self.current_text:  # 如果有未完成的文本，保存它
                self.finishTextInput()
            # 无论是否有文本，都需要完全退出文本输入模式
            self.is_text_input = False
            if self.text_cursor_timer and self.text_cursor_timer.isActive():
                self.text_cursor_timer.stop()
        
        # 设置当前工具
        self.current_tool = tool_name
        print(f"已选择工具: {tool_name}")
        
        # 显示对应的属性面板
        self.showPropertyPanel(tool_name)
        
        # 根据工具类型设置特定属性
        if tool_name == "text_input":
            self.is_text_input = True
            self.current_text = ""  # 重置当前文本，但不影响已保存的文本
            
            # 设置文本光标闪烁
            if self.text_cursor_timer is None:
                self.text_cursor_timer = QTimer(self)
                self.text_cursor_timer.timeout.connect(self.toggleTextCursor)
            if not self.text_cursor_timer.isActive():
                self.text_cursor_timer.start(500)
        
        # 如果选择了马赛克工具，不再显示对话框，改为使用属性面板控制
        elif tool_name == "mosaic":
            pass  # 已在属性面板中处理
        
        # 更新显示
        self.updateImageLabel()
    
    def setColor(self):
        """设置画笔颜色"""
        color = QColorDialog.getColor(self.pen_color, self)
        if color.isValid():
            self.pen_color = color
            print(f"设置颜色: {color.name()}")
    
    def setColorDirect(self, color):
        """直接设置预设颜色"""
        if color:
            self.pen_color = QColor(color)
            print(f"设置预设颜色: {color.name()}")
            
            # 如果是在文本输入模式下，确保更新后仍然保持文本输入状态
            if self.is_text_input:
                # 强制更新显示
                self.updateImageLabel()
                # 确保文本光标仍然可见并且焦点没有丢失
                if self.text_cursor_timer and not self.text_cursor_timer.isActive():
                    self.text_cursor_timer.start(500)
                
                # 确保窗口保持文本输入状态
                self.is_text_input = True
                # 返回键盘焦点到控件
                self.setFocus()
    
    def setFont(self):
        """设置文本字体"""
        font, ok = QFontDialog.getFont(self.text_font, self)
        if ok:
            self.text_font = font
            print(f"设置字体: {font.family()} {font.pointSize()}")
            
            # 如果是在文本输入模式下，确保更新后仍然保持文本输入状态
            if self.is_text_input:
                # 强制更新显示
                self.updateImageLabel()
                # 确保文本光标仍然可见并且焦点没有丢失
                if self.text_cursor_timer and not self.text_cursor_timer.isActive():
                    self.text_cursor_timer.start(500)
                
                # 确保窗口保持文本输入状态
                self.is_text_input = True
                # 返回键盘焦点到控件
                self.setFocus()
    
    def eventFilter(self, source, event):
        """事件过滤器，用于处理鼠标事件"""
        if source == self.image_label:
            # 处理鼠标按下事件
            if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                # 如果正在文本输入，处理文本点击
                if self.is_text_input:
                    # 如果有当前文本，先保存
                    if self.current_text:
                        self.finishTextInput()
                    
                    self.start_point = event.pos()
                    self.current_text = ""  # 清空当前文本，准备新输入
                    self.updateImageLabel()
                    return True
                
                # 检查是否点击了控制点（用于调整大小）
                shape_index, handle_index = self.getHandleAtPosition(event.pos())
                if shape_index >= 0 and handle_index >= 0:
                    print(f"开始调整形状大小 - 形状索引: {shape_index}, 控制点: {handle_index}")
                    # 开始调整大小
                    self.is_resizing = True
                    self.resize_shape_index = shape_index
                    self.resize_handle = handle_index
                    return True
                
                # 检查是否点击了已有形状
                shape_index = self.getShapeAtPosition(event.pos())
                if shape_index >= 0:
                    # 开始移动形状，所有形状都可以移动
                    print(f"开始移动形状 - 形状索引: {shape_index}")
                    self.is_moving_shape = True
                    self.moving_shape_index = shape_index
                    self.move_start_pos = event.pos()
                    return True
                else:
                    # 正常开始绘制
                    self.startDrawing(event.pos())
                    return True
                
            # 处理鼠标移动事件
            elif event.type() == event.MouseMove:
                # 如果在文本输入模式下移动鼠标，不做特殊处理
                if self.is_text_input:
                    return True
                
                # 更新鼠标指针样式
                shape_index, handle_index = self.getHandleAtPosition(event.pos())
                if shape_index >= 0 and handle_index >= 0:
                    if handle_index in [0, 3]:  # 左上角或右下角
                        self.image_label.setCursor(Qt.SizeFDiagCursor)
                    else:  # 右上角或左下角
                        self.image_label.setCursor(Qt.SizeBDiagCursor)
                elif self.getShapeAtPosition(event.pos()) >= 0:
                    self.image_label.setCursor(Qt.SizeAllCursor)
                else:
                    self.image_label.setCursor(Qt.ArrowCursor)
                
                # 处理调整大小
                if self.is_resizing and self.resize_shape_index >= 0:
                    self.resizeShape(event.pos())
                    return True
                # 处理移动形状
                elif self.is_moving_shape and self.moving_shape_index >= 0:
                    self.moveShape(event.pos())
                    return True
                # 处理绘制
                elif self.is_drawing:
                    self.drawing(event.pos())
                    return True
            
            # 处理鼠标释放事件
            elif event.type() == event.MouseButtonRelease and event.button() == Qt.LeftButton:
                # 如果在文本输入模式下释放鼠标，不做特殊处理
                if self.is_text_input:
                    return True
                
                if self.is_resizing:
                    # 完成调整大小
                    self.finishResizeShape()
                    return True
                elif self.is_moving_shape:
                    # 完成移动形状
                    self.finishMoveShape()
                    return True
                elif self.is_drawing:
                    # 完成绘制
                    self.endDrawing(event.pos())
                    return True
        
        return super().eventFilter(source, event)
    
    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        # 移除了拖动窗口功能
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        # 移除了拖动窗口功能
        super().mouseMoveEvent(event)
    
    def startDrawing(self, pos):
        """开始绘制"""
        if not self.current_tool:
            return
        
        # 如果在文本输入模式下，先完成当前文本输入
        if self.is_text_input and self.current_tool != "text_input":
            if self.current_text:
                self.finishTextInput()
            self.is_text_input = False
            if self.text_cursor_timer and self.text_cursor_timer.isActive():
                self.text_cursor_timer.stop()
        
        self.is_drawing = True
        self.start_point = pos
        self.end_point = pos
        
        # 如果是文本工具，提示用户输入文本
        if self.current_tool == "text":
            text, ok = QInputDialog.getText(self, "输入文本", "请输入要添加的文本:", QLineEdit.Normal, "")
            if ok and text:
                self.temp_text = text
                # 直接添加文本形状，不需要拖动
                shape = {
                    "type": "text",
                    "start": self.start_point,
                    "end": self.start_point,
                    "color": self.pen_color,
                    "font": self.text_font,
                    "text": self.temp_text
                }
                self.shapes.append(shape)
                self.updateImageLabel()
                self.is_drawing = False
        
        # 如果是直接文本输入，设置起始位置
        elif self.current_tool == "text_input":
            self.is_text_input = True
            self.current_text = ""  # 新的文本输入，重置当前文本
            self.start_point = pos  # 设置新文本的起始位置
            self.is_drawing = False
            
            # 确保文本光标闪烁
            if self.text_cursor_timer is None:
                self.text_cursor_timer = QTimer(self)
                self.text_cursor_timer.timeout.connect(self.toggleTextCursor)
            if not self.text_cursor_timer.isActive():
                self.text_cursor_timer.start(500)
            
            self.updateImageLabel()
            
        # 更新显示，确保视觉反馈
        self.updateImageLabel()
    
    def drawing(self, pos):
        """绘制过程"""
        if not self.is_drawing:
            return
        
        self.end_point = pos
        self.updateImageLabel()
    
    def endDrawing(self, pos):
        """结束绘制"""
        if not self.is_drawing:
            return
        
        self.end_point = pos
        
        # 如果起点和终点距离太小，不添加形状
        if (abs(self.start_point.x() - self.end_point.x()) < 5 and 
            abs(self.start_point.y() - self.end_point.y()) < 5):
            self.is_drawing = False
            return
        
        # 添加当前绘制的形状
        if self.current_tool == "rectangle":
            shape = {
                "type": "rectangle",
                "start": self.start_point,
                "end": self.end_point,
                "color": self.pen_color,
                "width": self.pen_width
            }
            self.shapes.append(shape)
        
        elif self.current_tool == "circle":
            shape = {
                "type": "circle",
                "start": self.start_point,
                "end": self.end_point,
                "color": self.pen_color,
                "width": self.pen_width
            }
            self.shapes.append(shape)
        
        elif self.current_tool == "arrow":
            shape = {
                "type": "arrow",
                "start": self.start_point,
                "end": self.end_point,
                "color": self.pen_color,
                "width": self.pen_width
            }
            self.shapes.append(shape)
        
        elif self.current_tool == "mosaic":
            shape = {
                "type": "mosaic",
                "start": self.start_point,
                "end": self.end_point,
                "size": self.mosaic_size
            }
            self.shapes.append(shape)
            self.applyMosaic(shape)  # 马赛克效果需要立即应用到pixmap
        
        self.is_drawing = False
        self.updateImageLabel()
    
    def updateImageLabel(self):
        """更新图像显示"""
        if not self.current_pixmap:
            return
        
        # 创建一个临时pixmap用于绘制
        temp_pixmap = QPixmap(self.current_pixmap)
        painter = QPainter(temp_pixmap)
        
        # 设置抗锯齿
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制已保存的形状
        for i, shape in enumerate(self.shapes):
            # 正常绘制形状
            self.drawShape(painter, shape)
            
            # 为可移动形状添加控制点（除马赛克外的所有形状）
            if shape["type"] in ["rectangle", "circle", "text"]:
                color = shape.get("color", QColor(255, 0, 0))
                
                # 绘制控制点
                if shape["type"] in ["rectangle", "circle"]:
                    rect = QRect(shape["start"], shape["end"]).normalized()
                    self.drawControlPoints(painter, rect, color)
                elif shape["type"] == "text" and "text" in shape:
                    # 为文本添加控制点
                    font_metrics = QFontMetrics(shape["font"])
                    text_width = font_metrics.width(shape["text"])
                    text_height = font_metrics.height()
                    text_rect = QRect(shape["start"].x(), shape["start"].y() - text_height,
                                    text_width, text_height)
                    self.drawControlPoints(painter, text_rect, color)
        
        # 绘制当前正在绘制的临时形状
        if self.is_drawing and self.current_tool:
            shape = {
                "type": self.current_tool,
                "start": self.start_point,
                "end": self.end_point,
                "color": self.pen_color,
                "width": self.pen_width
            }
            self.drawShape(painter, shape)
        
        # 绘制正在输入的文本
        if self.is_text_input:
            painter.setPen(QPen(self.pen_color))
            painter.setFont(self.text_font)
            
            # 绘制已输入的文本
            text_to_draw = self.current_text
            if self.start_point and text_to_draw:  # 确保有效的起始点和文本
                painter.drawText(self.start_point, text_to_draw)
            
            # 计算光标位置
            if self.text_cursor_visible and self.start_point:
                # 计算文本宽度
                font_metrics = painter.fontMetrics()
                text_width = font_metrics.width(text_to_draw)
                
                # 绘制光标
                cursor_x = self.start_point.x() + text_width
                cursor_y = self.start_point.y()
                cursor_height = font_metrics.height()
                
                # 绘制垂直线作为光标
                painter.drawLine(cursor_x, cursor_y - cursor_height + 2, cursor_x, cursor_y + 2)
        
        painter.end()
        
        # 更新图像标签
        self.image_label.setPixmap(temp_pixmap)
        # 确保标签尺寸与pixmap一致，避免拉伸问题
        self.image_label.setFixedSize(temp_pixmap.size())
    
    def drawShape(self, painter, shape):
        """根据形状类型绘制对应图形"""
        shape_type = shape.get("type")
        
        # 确保shape包含所有必要的键
        if not all(key in shape for key in ["start", "end"]):
            return
        
        start = shape["start"]
        end = shape["end"]
        
        if shape_type in ["rectangle", "circle", "arrow"]:
            if "color" not in shape or "width" not in shape:
                return
            
            color = shape["color"]
            width = shape["width"]
            
            pen = QPen(color, width)
            painter.setPen(pen)
            
            # 使用NoBrush确保矩形和圆形只绘制边框
            painter.setBrush(Qt.NoBrush)
            
            if shape_type == "rectangle":
                rect = QRect(start, end)
                painter.drawRect(rect.normalized())
            
            elif shape_type == "circle":
                rect = QRect(start, end)
                painter.drawEllipse(rect.normalized())
            
            elif shape_type == "arrow":
                self.drawArrow(painter, start, end, color, width)
        
        elif shape_type == "text":
            # 确保包含所有必要的键
            if not all(key in shape for key in ["color", "font", "text"]):
                return
            
            color = shape["color"]
            font = shape["font"]
            text = shape["text"]
            painter.setPen(QPen(color))
            painter.setFont(font)
            painter.drawText(start, text)
        
        # 马赛克已经应用到pixmap上，不需要在这里绘制
    
    def drawArrow(self, painter, start, end, color, width):
        """绘制箭头"""
        # 绘制线段
        painter.drawLine(start, end)
        
        # 计算箭头
        arrow_size = max(15, width * 5)  # 箭头大小与线条粗细成比例
        angle = 20  # 更尖锐的箭头角度（度）
        
        # 计算线段角度
        line_length = ((end.x() - start.x())**2 + (end.y() - start.y())**2)**0.5
        if line_length == 0:
            return
        
        # 计算单位向量
        dx = (end.x() - start.x()) / line_length
        dy = (end.y() - start.y()) / line_length
        
        # 计算箭头两边的点（使用正确的三角函数）
        angle_rad = angle * 3.14159 / 180.0  # 转换为弧度
        
        # 计算箭头两翼的点
        x1 = end.x() - arrow_size * (dx * math.cos(angle_rad) + dy * math.sin(angle_rad))
        y1 = end.y() - arrow_size * (dy * math.cos(angle_rad) - dx * math.sin(angle_rad))
        
        x2 = end.x() - arrow_size * (dx * math.cos(angle_rad) - dy * math.sin(angle_rad))
        y2 = end.y() - arrow_size * (dy * math.cos(angle_rad) + dx * math.sin(angle_rad))
        
        # 创建填充的箭头
        points = [end, QPoint(int(x1), int(y1)), QPoint(int(x2), int(y2))]
        
        # 保存当前画笔和画刷
        old_pen = painter.pen()
        old_brush = painter.brush()
        
        # 设置填充色与线条颜色相同
        painter.setBrush(QBrush(color))
        
        # 绘制填充的箭头
        painter.drawPolygon(points)
        
        # 恢复原来的画笔和画刷
        painter.setPen(old_pen)
        painter.setBrush(old_brush)
    
    def applyMosaic(self, shape):
        """应用马赛克效果到图像"""
        # 获取选定区域
        rect = QRect(shape["start"], shape["end"]).normalized()
        size = shape["size"]
        
        # 创建一个临时QImage用于处理
        image = self.current_pixmap.toImage()
        
        # 边框宽度（确保不对边框应用马赛克）
        border_width = 2
        
        # 确保马赛克区域不超出图像边界并且不影响边框
        safe_rect = rect.intersected(QRect(border_width, border_width, 
                                        image.width() - 2 * border_width, 
                                        image.height() - 2 * border_width))
        
        # 遍历选定区域的每个马赛克块
        for x in range(safe_rect.left(), safe_rect.right(), size):
            for y in range(safe_rect.top(), safe_rect.bottom(), size):
                # 确保不超出图像边界
                block_width = min(size, safe_rect.right() - x)
                block_height = min(size, safe_rect.bottom() - y)
                
                if block_width <= 0 or block_height <= 0:
                    continue
                
                # 计算块内平均颜色
                r, g, b, count = 0, 0, 0, 0
                for dx in range(block_width):
                    for dy in range(block_height):
                        px, py = x + dx, y + dy
                        if safe_rect.contains(px, py):
                            pixel = image.pixel(px, py)
                            r += QColor(pixel).red()
                            g += QColor(pixel).green()
                            b += QColor(pixel).blue()
                            count += 1
                
                if count > 0:
                    avg_color = QColor(r // count, g // count, b // count)
                    
                    # 将块内所有像素设为平均颜色
                    for dx in range(block_width):
                        for dy in range(block_height):
                            px, py = x + dx, y + dy
                            if safe_rect.contains(px, py):
                                image.setPixel(px, py, avg_color.rgb())
        
        # 更新当前pixmap
        self.current_pixmap = QPixmap.fromImage(image)
    
    def undo(self):
        """撤销上一步操作"""
        if self.shapes:
            self.shapes.pop()
            # 对于马赛克，需要重新加载原始图像并重新应用所有操作
            if any(shape["type"] == "mosaic" for shape in self.shapes):
                # 加载带边框的原始图像
                self.current_pixmap = self.addBorderToPixmap(self.original_pixmap)
                for shape in self.shapes:
                    if shape["type"] == "mosaic":
                        self.applyMosaic(shape)
            self.updateImageLabel()
            print("撤销上一步操作")
    
    def clearAll(self):
        """清除所有绘制内容"""
        self.shapes = []
        # 重新加载带边框的原始图像
        self.current_pixmap = self.addBorderToPixmap(self.original_pixmap)
        self.updateImageLabel()
        print("清除所有内容")
    
    def saveImage(self):
        """保存编辑后的图像到文件,并隐藏编辑器"""
        # 确保完成所有文本输入
        if self.is_text_input and self.current_text:
            self.finishTextInput()
        
        # 获取原始图像并应用编辑内容
        if self.original_pixmap:
            # 创建一个临时的pixmap,使用原始图像(无边框)
            temp_pixmap = QPixmap(self.original_pixmap)
            painter = QPainter(temp_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 绘制所有形状
            for shape in self.shapes:
                # 需要调整形状的坐标，去掉边框偏移
                self.drawShapeWithoutBorder(painter, shape)
                
            painter.end()
            
            # 打开文件保存对话框
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
            default_filename = os.path.expanduser(f"~/Pictures/{timestamp}.png")
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存截图",
                default_filename,
                "Images (*.png *.jpg *.jpeg *.bmp)"
            )
            
            if file_path:
                # 保存图像
                temp_pixmap.save(file_path)
                print(f"图像已保存到: {file_path}")
            
            # 发出信号,通知截图编辑完成
            self.editingFinished.emit(temp_pixmap)
            
            # 隐藏窗口而不是关闭
            self.hide()
            
            # 清空当前绘制内容,准备下次使用
            self.shapes = []
            # 重新加载带边框的原始图像，因为现在回到了编辑模式
            self.current_pixmap = self.addBorderToPixmap(self.original_pixmap)
            self.updateImageLabel()
            
    def copyToClipboard(self):
        """复制当前图像到剪贴板，包含所有编辑内容但不包含边框"""
        if self.original_pixmap:
            # 创建一个临时的pixmap，使用原始图像(无边框)
            temp_pixmap = QPixmap(self.original_pixmap)
            painter = QPainter(temp_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 绘制所有形状
            for shape in self.shapes:
                # 需要调整形状的坐标，去掉边框偏移
                self.drawShapeWithoutBorder(painter, shape)
            
            # 如果正在输入文本，完成文本输入
            if self.is_text_input and self.current_text:
                self.finishTextInput()
                
            painter.end()
            
            # 将带有所有编辑内容的图像复制到剪贴板
            QApplication.clipboard().setPixmap(temp_pixmap)
            print("已复制带有标记的图像到剪贴板")
            
            # 发出编辑完成信号但不复制到剪贴板
            self.editingFinished.emit(temp_pixmap)
            print("已隐藏编辑界面")
        
        # 清空当前绘制内容，准备下次使用
        self.shapes = []
        # 重新加载带边框的原始图像，因为现在回到了编辑模式
        self.current_pixmap = self.addBorderToPixmap(self.original_pixmap)
        self.updateImageLabel()
        
        # 隐藏窗口但不关闭
        self.hide()
        
    def hideEditor(self):
        """隐藏编辑器，清空内容，准备下次使用"""
        # 如果正在输入文本，结束文本输入
        if self.is_text_input and self.current_text:
            self.finishTextInput()
        
        # 获取原始图像并应用编辑内容
        if self.original_pixmap:
            # 创建一个临时的pixmap，使用原始图像(无边框)
            temp_pixmap = QPixmap(self.original_pixmap)
            painter = QPainter(temp_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 绘制所有形状
            for shape in self.shapes:
                # 需要调整形状的坐标，去掉边框偏移
                self.drawShapeWithoutBorder(painter, shape)
                
            painter.end()
            
            # 发出编辑完成信号但不复制到剪贴板
            self.editingFinished.emit(temp_pixmap)
            print("已隐藏编辑界面")
        
        # 清空当前绘制内容，准备下次使用
        self.shapes = []
        # 重新加载带边框的原始图像，因为现在回到了编辑模式
        self.current_pixmap = self.addBorderToPixmap(self.original_pixmap)
        self.updateImageLabel()
        
        # 隐藏窗口但不关闭
        self.hide()
        
    def drawShapeWithoutBorder(self, painter, shape):
        """绘制形状到无边框图像上，需要调整坐标"""
        shape_type = shape.get("type")
        
        # 确保shape包含所有必要的键
        if not all(key in shape for key in ["start", "end"]):
            return
        
        # 边框宽度
        border_width = 2
        
        # 获取调整后的起点和终点（去掉边框的偏移）
        start = QPoint(shape["start"].x() - border_width, shape["start"].y() - border_width)
        end = QPoint(shape["end"].x() - border_width, shape["end"].y() - border_width)
        
        if shape_type in ["rectangle", "circle", "arrow"]:
            if "color" not in shape or "width" not in shape:
                return
            
            color = shape["color"]
            width = shape["width"]
            
            pen = QPen(color, width)
            painter.setPen(pen)
            
            # 使用NoBrush确保矩形和圆形只绘制边框
            painter.setBrush(Qt.NoBrush)
            
            if shape_type == "rectangle":
                rect = QRect(start, end)
                painter.drawRect(rect.normalized())
            
            elif shape_type == "circle":
                rect = QRect(start, end)
                painter.drawEllipse(rect.normalized())
            
            elif shape_type == "arrow":
                self.drawArrow(painter, start, end, color, width)
        
        elif shape_type == "text":
            # 确保包含所有必要的键
            if not all(key in shape for key in ["color", "font", "text"]):
                return
            
            color = shape["color"]
            font = shape["font"]
            text = shape["text"]
            painter.setPen(QPen(color))
            painter.setFont(font)
            painter.drawText(start, text)
            
        # 注意：马赛克效果需要特殊处理，因为已经应用到了pixmap上
        # 在保存/复制时需要额外处理马赛克区域
        elif shape_type == "mosaic":
            # 马赛克已经应用到pixmap上，不需要在这里特别处理
            # 因为我们是从原始图像重新开始的，所以需要重新应用马赛克
            if "size" in shape:
                # 创建一个调整后的马赛克形状（去掉边框偏移）
                adjusted_shape = {
                    "type": "mosaic",
                    "start": start,
                    "end": end,
                    "size": shape["size"]
                }
                
                # 获取选定区域
                rect = QRect(start, end).normalized()
                size = shape["size"]
                
                # 创建一个临时QImage用于处理
                image = painter.device().toImage()
                
                # 遍历选定区域的每个马赛克块
                for x in range(rect.left(), rect.right(), size):
                    for y in range(rect.top(), rect.bottom(), size):
                        # 确保不超出图像边界
                        block_width = min(size, rect.right() - x)
                        block_height = min(size, rect.bottom() - y)
                        
                        if block_width <= 0 or block_height <= 0:
                            continue
                        
                        # 计算块内平均颜色
                        r, g, b, count = 0, 0, 0, 0
                        for dx in range(block_width):
                            for dy in range(block_height):
                                px, py = x + dx, y + dy
                                if rect.contains(px, py) and px >= 0 and py >= 0 and px < image.width() and py < image.height():
                                    pixel = image.pixel(px, py)
                                    r += QColor(pixel).red()
                                    g += QColor(pixel).green()
                                    b += QColor(pixel).blue()
                                    count += 1
                        
                        if count > 0:
                            avg_color = QColor(r // count, g // count, b // count)
                            
                            # 填充马赛克块
                            painter.fillRect(QRect(x, y, block_width, block_height), avg_color)

    def getShapeAtPosition(self, pos):
        """检查指定位置是否有形状，返回形状索引"""
        # 从后向前检查，以便后绘制的形状优先
        for i in range(len(self.shapes)-1, -1, -1):
            shape = self.shapes[i]
            if shape["type"] == "rectangle":
                rect = QRect(shape["start"], shape["end"]).normalized()
                # 检查是否在边框附近（边框宽度的2倍范围内）
                border_width = shape.get("width", 2) * 2
                outer_rect = rect.adjusted(-border_width, -border_width, border_width, border_width)
                inner_rect = rect.adjusted(border_width, border_width, -border_width, -border_width)
                
                # 如果在边框区域或内部区域
                if outer_rect.contains(pos) and not inner_rect.contains(pos):
                    return i
                # 如果是小矩形，整个区域都可以点击
                if rect.width() < 20 or rect.height() < 20:
                    if rect.contains(pos):
                        return i
                
            elif shape["type"] == "circle":
                rect = QRect(shape["start"], shape["end"]).normalized()
                center = rect.center()
                rx = rect.width() / 2
                ry = rect.height() / 2
                
                # 计算点到椭圆的距离，近似值
                if rx > 0 and ry > 0:
                    dx = (pos.x() - center.x()) / rx
                    dy = (pos.y() - center.y()) / ry
                    distance = dx*dx + dy*dy
                    
                    # 在椭圆边框附近（边框宽度的2倍范围内）
                    border_width = shape.get("width", 2) * 2 / min(rx, ry)
                    if abs(distance - 1.0) < border_width:
                        return i
                    # 如果是小圆形，整个区域都可以点击
                    if rect.width() < 20 or rect.height() < 20:
                        if distance <= 1.0:
                            return i
            
            elif shape["type"] == "text" and "text" in shape:
                # 为文本创建一个小的检测区域
                font_metrics = QFontMetrics(shape["font"])
                text_width = font_metrics.width(shape["text"])
                text_height = font_metrics.height()
                text_rect = QRect(shape["start"].x(), shape["start"].y() - text_height,
                                text_width, text_height)
                if text_rect.contains(pos):
                    return i
        return -1
    
    def moveShape(self, pos):
        """移动当前选中的形状"""
        if self.moving_shape_index < 0 or self.moving_shape_index >= len(self.shapes):
            return
        
        # 计算移动距离
        delta_x = pos.x() - self.move_start_pos.x()
        delta_y = pos.y() - self.move_start_pos.y()
        
        # 获取当前形状
        shape = self.shapes[self.moving_shape_index]
        
        # 移动形状的起点和终点（适用于所有形状）
        shape["start"] = QPoint(shape["start"].x() + delta_x, shape["start"].y() + delta_y)
        shape["end"] = QPoint(shape["end"].x() + delta_x, shape["end"].y() + delta_y)
        
        # 更新移动起始位置
        self.move_start_pos = pos
        
        # 更新显示
        self.updateImageLabel()
    
    def finishMoveShape(self):
        """完成形状移动"""
        self.is_moving_shape = False
        self.moving_shape_index = -1
        self.move_start_pos = QPoint()

    def drawControlPoints(self, painter, rect, color):
        """绘制形状的控制点"""
        size = 10  # 增大控制点尺寸
        pen = QPen(color, 2)  # 增加边框宽度
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.white))  # 使用白色填充，更容易看到
        
        # 左上角
        painter.drawRect(rect.left() - size // 2, rect.top() - size // 2, size, size)
        # 右上角
        painter.drawRect(rect.right() - size // 2, rect.top() - size // 2, size, size)
        # 左下角
        painter.drawRect(rect.left() - size // 2, rect.bottom() - size // 2, size, size)
        # 右下角
        painter.drawRect(rect.right() - size // 2, rect.bottom() - size // 2, size, size)

    def inputMethodEvent(self, event):
        """处理输入法事件，支持中文输入"""
        if not self.is_text_input:
            return
        
        # 获取预编辑文本（输入法组合阶段）
        preedit_text = event.preeditString()
        
        # 获取提交的文本（确认输入的内容）
        commit_text = event.commitString()
        
        # 如果有提交的文本，加入到当前文本中
        if commit_text:
            self.current_text += commit_text
            self.updateImageLabel()
        
        # 更新显示（包含预编辑文本的预览）
        if preedit_text or commit_text:
            self.updateTextWithPreedit(preedit_text)
        
        # 接受事件
        event.accept()

    def updateTextWithPreedit(self, preedit_text):
        """更新带有预编辑文本的显示"""
        if not self.is_text_input:
            return
        
        # 临时pixmap用于绘制
        temp_pixmap = QPixmap(self.current_pixmap)
        painter = QPainter(temp_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制已保存的形状
        for shape in self.shapes:
            self.drawShape(painter, shape)
        
        # 绘制当前文本和预编辑文本
        painter.setPen(QPen(self.pen_color))
        painter.setFont(self.text_font)
        
        # 绘制确认的文本
        painter.drawText(self.start_point, self.current_text)
        
        # 绘制预编辑文本（如果有）
        if preedit_text:
            font_metrics = painter.fontMetrics()
            confirmed_text_width = font_metrics.width(self.current_text)
            
            # 计算预编辑文本的位置
            preedit_pos = QPoint(self.start_point.x() + confirmed_text_width, self.start_point.y())
            
            # 绘制预编辑文本，使用不同的颜色
            painter.setPen(QPen(QColor(100, 100, 255)))  # 使用蓝色显示预编辑文本
            painter.drawText(preedit_pos, preedit_text)
            
            # 恢复原笔颜色
            painter.setPen(QPen(self.pen_color))
        
        # 绘制光标
        if self.text_cursor_visible:
            font_metrics = painter.fontMetrics()
            total_text_width = font_metrics.width(self.current_text + preedit_text)
            
            cursor_x = self.start_point.x() + total_text_width
            cursor_y = self.start_point.y()
            cursor_height = font_metrics.height()
            
            painter.drawLine(cursor_x, cursor_y - cursor_height + 2, cursor_x, cursor_y + 2)
        
        painter.end()
        
        # 更新图像标签
        self.image_label.setPixmap(temp_pixmap)

    def showPropertyPanel(self, tool_type):
        """根据工具类型显示不同的属性面板"""
        # 清除旧的属性面板内容
        while self.property_layout.count():
            item = self.property_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 根据工具类型添加不同的控件
        if tool_type in ["rectangle", "circle", "arrow"]:  # 添加箭头到共享样式工具
            # 添加边框颜色选择器
            self.property_layout.addWidget(QLabel("颜色:"))
            
            # 颜色预设面板
            color_preset_layout = QHBoxLayout()
            color_preset_layout.setSpacing(2)
            
            # 常用颜色预设 - 使用 QColor 对象而不是 Qt.GlobalColor
            colors = [QColor(255, 0, 0), QColor(0, 0, 255), QColor(0, 255, 0), 
                      QColor(255, 255, 0), QColor(0, 0, 0), QColor(255, 255, 255)]
            
            for c in colors:
                color_btn = QPushButton()
                color_btn.setFixedSize(20, 20)
                color_btn.setStyleSheet(f"background-color: {c.name()}; border: 1px solid #888888;")
                color_btn.clicked.connect(lambda checked, color=c: self.setColorDirect(color))
                color_preset_layout.addWidget(color_btn)
            
            # 自定义颜色按钮
            custom_color_btn = QPushButton("自定义...")
            custom_color_btn.setFixedWidth(60)
            custom_color_btn.clicked.connect(self.setColor)
            color_preset_layout.addWidget(custom_color_btn)
            
            color_widget = QWidget()
            color_widget.setLayout(color_preset_layout)
            self.property_layout.addWidget(color_widget)
            
            # 添加边框粗细滑块
            self.property_layout.addWidget(QLabel("粗细:"))
            width_slider = QSlider(Qt.Horizontal)
            width_slider.setMinimum(1)
            width_slider.setMaximum(10)
            width_slider.setValue(self.pen_width)
            width_slider.setFixedWidth(100)
            width_slider.valueChanged.connect(self.setPenWidth)
            
            # 显示当前值的标签
            width_label = QLabel(f"{self.pen_width}px")
            width_label.setFixedWidth(30)
            width_slider.valueChanged.connect(lambda v: width_label.setText(f"{v}px"))
            
            width_layout = QHBoxLayout()
            width_layout.addWidget(width_slider)
            width_layout.addWidget(width_label)
            
            width_widget = QWidget()
            width_widget.setLayout(width_layout)
            self.property_layout.addWidget(width_widget)
            
        elif tool_type == "text_input":
            # 添加文本颜色选择器
            self.property_layout.addWidget(QLabel("文本颜色:"))
            
            # 颜色预设面板
            color_preset_layout = QHBoxLayout()
            color_preset_layout.setSpacing(2)
            
            # 常用颜色预设 - 使用 QColor 对象而不是 Qt.GlobalColor
            colors = [QColor(255, 0, 0), QColor(0, 0, 255), QColor(0, 255, 0), 
                      QColor(255, 255, 0), QColor(0, 0, 0), QColor(255, 255, 255)]
            
            for c in colors:
                color_btn = QPushButton()
                color_btn.setFixedSize(20, 20)
                color_btn.setStyleSheet(f"background-color: {c.name()}; border: 1px solid #888888;")
                color_btn.clicked.connect(lambda checked, color=c: self.setColorDirect(color))
                color_preset_layout.addWidget(color_btn)
            
            # 自定义颜色按钮
            custom_color_btn = QPushButton("自定义...")
            custom_color_btn.setFixedWidth(60)
            custom_color_btn.clicked.connect(self.setColor)
            color_preset_layout.addWidget(custom_color_btn)
            
            color_widget = QWidget()
            color_widget.setLayout(color_preset_layout)
            self.property_layout.addWidget(color_widget)
            
            # 添加字体大小选择器
            self.property_layout.addWidget(QLabel("字号:"))
            font_size_combo = QComboBox()
            font_sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72]
            for size in font_sizes:
                font_size_combo.addItem(str(size), size)
            font_size_combo.setCurrentText(str(self.text_font.pointSize()))
            font_size_combo.currentIndexChanged.connect(lambda: self.setFontSize(font_size_combo.currentData()))
            font_size_combo.setFixedWidth(60)
            self.property_layout.addWidget(font_size_combo)
            
            # 添加粗体复选框
            bold_check = QCheckBox("粗体")
            bold_check.setChecked(self.text_bold)
            bold_check.stateChanged.connect(self.toggleBold)
            self.property_layout.addWidget(bold_check)
            
        elif tool_type == "mosaic":
            # 添加马赛克大小滑块
            self.property_layout.addWidget(QLabel("马赛克大小:"))
            mosaic_slider = QSlider(Qt.Horizontal)
            mosaic_slider.setMinimum(2)
            mosaic_slider.setMaximum(50)
            mosaic_slider.setValue(self.mosaic_size)
            mosaic_slider.setFixedWidth(150)
            mosaic_slider.valueChanged.connect(self.setMosaicSize)
            
            # 显示当前大小
            size_label = QLabel(f"{self.mosaic_size}px")
            size_label.setFixedWidth(40)
            size_label.setObjectName("mosaic_size_label")
            
            # 马赛克slider值变化时更新标签
            mosaic_slider.valueChanged.connect(lambda v: size_label.setText(f"{v}px"))
            
            mosaic_layout = QHBoxLayout()
            mosaic_layout.addWidget(mosaic_slider)
            mosaic_layout.addWidget(size_label)
            
            mosaic_widget = QWidget()
            mosaic_widget.setLayout(mosaic_layout)
            self.property_layout.addWidget(mosaic_widget)
        
        # 添加弹性空间，使控件靠左对齐
        self.property_layout.addStretch()
        
        # 显示属性面板
        self.property_panel.show()
        self.property_panel_visible = True
        
        # 调整窗口大小
        min_width = 600  # 确保工具栏能完整显示的最小宽度
        if self.current_pixmap:
            # 确保宽度不小于最小宽度
            window_width = max(self.current_pixmap.width(), min_width)
            self.resize(window_width, self.current_pixmap.height() + 100)  # +100为工具栏和属性面板高度

    def setPenWidth(self, width):
        """设置边框粗细"""
        self.pen_width = width
        print(f"设置边框粗细: {width}")

    def setMosaicSize(self, size):
        """设置马赛克大小"""
        self.mosaic_size = size
        print(f"设置马赛克大小: {size}")

    def setFontSize(self, size):
        """设置字体大小"""
        if size:
            font = self.text_font
            font.setPointSize(size)
            self.text_font = font
            print(f"设置字体大小: {size}")
            
            # 如果是在文本输入模式下，确保更新后仍然保持文本输入状态
            if self.is_text_input:
                self.updateImageLabel()
                if self.text_cursor_timer and not self.text_cursor_timer.isActive():
                    self.text_cursor_timer.start(500)
                
                # 确保窗口保持文本输入状态
                self.is_text_input = True
                # 返回键盘焦点到控件
                self.setFocus()

    def toggleBold(self, state):
        """切换粗体状态"""
        self.text_bold = state == Qt.Checked
        font = self.text_font
        font.setBold(self.text_bold)
        self.text_font = font
        print(f"粗体状态: {self.text_bold}")
        
        # 如果是在文本输入模式下，确保更新后仍然保持文本输入状态
        if self.is_text_input:
            self.updateImageLabel()
            if self.text_cursor_timer and not self.text_cursor_timer.isActive():
                self.text_cursor_timer.start(500)
            
            # 确保窗口保持文本输入状态
            self.is_text_input = True
            # 返回键盘焦点到控件
            self.setFocus()

    def resizeShape(self, pos):
        """调整当前选中形状的大小"""
        if self.resize_shape_index < 0 or self.resize_shape_index >= len(self.shapes):
            return
        
        # 获取当前形状
        shape = self.shapes[self.resize_shape_index]
        if shape["type"] not in ["rectangle", "circle"]:
            return
        
        # 获取规范化的矩形（确保左上角是start，右下角是end）
        rect = QRect(shape["start"], shape["end"]).normalized()
        left = rect.left()
        top = rect.top()
        right = rect.right()
        bottom = rect.bottom()
        
        # 根据控制点调整矩形大小
        if self.resize_handle == 0:  # 左上角
            left = pos.x()
            top = pos.y()
        elif self.resize_handle == 1:  # 右上角
            right = pos.x()
            top = pos.y()
        elif self.resize_handle == 2:  # 左下角
            left = pos.x()
            bottom = pos.y()
        elif self.resize_handle == 3:  # 右下角
            right = pos.x()
            bottom = pos.y()
        
        # 创建新的矩形
        new_rect = QRect(QPoint(left, top), QPoint(right, bottom)).normalized()
        
        # 确保矩形不会太小
        min_size = 5
        if new_rect.width() < min_size:
            if self.resize_handle in [0, 2]:  # 左边控制点
                new_rect.setLeft(new_rect.right() - min_size)
            else:  # 右边控制点
                new_rect.setRight(new_rect.left() + min_size)
        
        if new_rect.height() < min_size:
            if self.resize_handle in [0, 1]:  # 上边控制点
                new_rect.setTop(new_rect.bottom() - min_size)
            else:  # 下边控制点
                new_rect.setBottom(new_rect.top() + min_size)
        
        # 更新形状的起点和终点
        shape["start"] = new_rect.topLeft()
        shape["end"] = new_rect.bottomRight()
        
        # 更新显示
        self.updateImageLabel()

    def finishResizeShape(self):
        """完成形状大小调整"""
        self.is_resizing = False
        self.resize_shape_index = -1
        self.resize_handle = -1
        self.image_label.setCursor(Qt.ArrowCursor)

    def addBorderToPixmap(self, pixmap):
        """为pixmap添加2px的蓝色边框"""
        if not pixmap:
            return QPixmap()
            
        # 创建一个比原图大4px的pixmap(左右上下各增加2px)
        border_width = 2  # 边框宽度
        width = pixmap.width() + border_width * 2
        height = pixmap.height() + border_width * 2
        
        # 创建新的pixmap并填充透明背景
        bordered_pixmap = QPixmap(width, height)
        bordered_pixmap.fill(Qt.transparent)
        
        # 创建画家
        painter = QPainter(bordered_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制蓝色边框
        border_color = QColor(0, 120, 215)  # 蓝色
        painter.setPen(QPen(border_color, border_width))
        
        # 绘制边框矩形，确保边框完全在pixmap内部
        border_rect = QRect(border_width//2, border_width//2, 
                          width - border_width, height - border_width)
        painter.drawRect(border_rect)
        
        # 在中心绘制原始图像
        painter.drawPixmap(border_width, border_width, pixmap)
        
        painter.end()
        
        return bordered_pixmap

    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 退出编辑器
        if event.key() == Qt.Key_Escape:
            # 如果正在输入文本，先取消输入
            if self.is_text_input:
                if self.current_text:  # 如果有文本，保存它
                    self.finishTextInput()
                else:  # 如果没有文本，退出文本模式
                    self.is_text_input = False
                    self.current_text = ""
                    if self.text_cursor_timer and self.text_cursor_timer.isActive():
                        self.text_cursor_timer.stop()
                    self.current_tool = None  # 取消当前工具选择
                    self.updateImageLabel()
                return  # 不关闭窗口，只退出文本模式
            self.close()
        # 回车完成输入
        elif self.is_text_input and (event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter):
            self.finishTextInput()
        # 退格键删除文本
        elif self.is_text_input and event.key() == Qt.Key_Backspace:
            if self.current_text:
                self.current_text = self.current_text[:-1]
                self.updateImageLabel()
        # 处理中文输入法组合键
        elif event.key() == Qt.Key_Shift or event.key() == Qt.Key_Control or event.key() == Qt.Key_Alt:
            # 忽略这些修饰键的独立按键事件
            pass
        elif self.is_text_input:
            # 不在这里处理文本，使用inputMethodEvent来处理中文输入
            pass
        else:
            super().keyPressEvent(event)
    
    def toggleTextCursor(self):
        """切换文本光标的可见状态"""
        if self.is_text_input:
            self.text_cursor_visible = not self.text_cursor_visible
            self.updateImageLabel()
    
    def finishTextInput(self):
        """完成文本输入并保存"""
        if self.is_text_input and self.current_text and self.start_point:
            # 创建文本形状
            shape = {
                "type": "text",
                "start": self.start_point,
                "end": self.start_point,
                "color": self.pen_color,
                "font": self.text_font,
                "text": self.current_text
            }
            self.shapes.append(shape)
            print(f"添加文本: {self.current_text}")
        
            # 重置文本输入状态但保持工具选中
            self.current_text = ""
            
            # 保持is_text_input为True，以便可以继续输入文本
            # 停止光标闪烁但准备重新开始
            if self.text_cursor_timer and self.text_cursor_timer.isActive():
                self.text_cursor_timer.stop()
                
            # 更新显示
            self.updateImageLabel()
            
            # 让光标继续闪烁，准备下一次输入
            if self.text_cursor_timer:
                self.text_cursor_timer.start(500)
            
            return True  # 返回True表示成功添加了文本
        elif self.is_text_input:
            # 如果没有文本但正在文本输入模式，只重置当前文本
            self.current_text = ""
            return False  # 返回False表示没有添加文本
            
    def getHandleAtPosition(self, pos):
        """检查指定位置是否有控制点，返回(形状索引, 控制点索引)"""
        handle_size = 12  # 增大控制点检测范围，使其更容易选中
        
        # 从后向前检查，以便后绘制的形状优先
        for i in range(len(self.shapes)-1, -1, -1):
            shape = self.shapes[i]
            if shape["type"] in ["rectangle", "circle"]:
                rect = QRect(shape["start"], shape["end"]).normalized()
                
                # 检查四个角落的控制点
                # 左上角
                if abs(pos.x() - rect.left()) <= handle_size and abs(pos.y() - rect.top()) <= handle_size:
                    return i, 0
                # 右上角
                if abs(pos.x() - rect.right()) <= handle_size and abs(pos.y() - rect.top()) <= handle_size:
                    return i, 1
                # 左下角
                if abs(pos.x() - rect.left()) <= handle_size and abs(pos.y() - rect.bottom()) <= handle_size:
                    return i, 2
                # 右下角
                if abs(pos.x() - rect.right()) <= handle_size and abs(pos.y() - rect.bottom()) <= handle_size:
                    return i, 3
        
        return -1, -1

def edit_screenshot(pixmap, screen_pos=None):
    """创建并显示截图编辑器"""
    editor = ScreenshotEditor(pixmap, screen_pos)
    return editor

if __name__ == "__main__":
    # 测试代码
    app = QApplication(sys.argv)
    
    # 创建一个测试用的空白图片
    test_pixmap = QPixmap(800, 600)
    test_pixmap.fill(Qt.white)
    
    # 创建编辑器
    editor = edit_screenshot(test_pixmap)
    
    sys.exit(app.exec_()) 