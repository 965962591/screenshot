from PyQt5.QtWidgets import (QWidget, QApplication, QLabel, QVBoxLayout, QHBoxLayout,
                           QPushButton, QToolBar, QAction, QColorDialog, QFontDialog,
                           QSizePolicy, QInputDialog, QLineEdit, QSlider)
from PyQt5.QtCore import Qt, QPoint, QRect, QSize, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont, QIcon, QBrush, QCursor, QFontMetrics

import os
import sys

class ScreenshotEditor(QWidget):
    """用于编辑截图的窗口，提供各种编辑工具"""
    
    # 定义一个信号，用于通知截图编辑完成
    editingFinished = pyqtSignal(QPixmap)
    
    def __init__(self, pixmap=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 保存原始图像和当前编辑的图像
        self.original_pixmap = pixmap
        self.current_pixmap = QPixmap(pixmap) if pixmap else QPixmap(800, 600)
        
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
        
        # 添加可移动的ROI矩形标记工具
        self.is_roi_tool = False  # 是否使用ROI工具
        
        # 启用输入法支持
        self.setAttribute(Qt.WA_InputMethodEnabled, True)
        
        self.initUI()
    
    def initUI(self):
        # 创建布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建图像显示区域
        self.image_label = QLabel()
        self.image_label.setPixmap(self.current_pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMouseTracking(True)
        self.image_label.installEventFilter(self)
        
        # 创建工具栏
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(32, 32))
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #3D3D3D;
                border: none;
                spacing: 2px;
                padding: 5px;
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
        
        # 将组件添加到布局
        main_layout.addWidget(self.image_label)
        main_layout.addWidget(self.toolbar)
        
        self.setLayout(main_layout)
        
        # 设置窗口大小
        if self.current_pixmap:
            self.resize(self.current_pixmap.width(), self.current_pixmap.height() + 50)  # +50 为工具栏高度
        else:
            self.resize(800, 650)
        
        # 启用输入法
        self.setAttribute(Qt.WA_InputMethodEnabled, True)
        
        self.updateImageLabel()
        self.show()
    
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
        save_action.setToolTip("保存并返回")
        save_action.triggered.connect(self.saveImage)
        self.toolbar.addAction(save_action)
        
        # 取消按钮
        cancel_action = QAction("取消", self)
        cancel_pixmap = QPixmap(24, 24)
        cancel_pixmap.fill(Qt.transparent)
        cancel_painter = QPainter(cancel_pixmap)
        cancel_painter.setPen(QPen(Qt.white, 2))
        cancel_painter.drawLine(6, 6, 18, 18)
        cancel_painter.drawLine(6, 18, 18, 6)
        cancel_painter.end()
        cancel_action.setIcon(QIcon(cancel_pixmap))
        cancel_action.setToolTip("取消编辑并返回")
        cancel_action.triggered.connect(self.close)
        self.toolbar.addAction(cancel_action)
    
    def setTool(self, tool_name):
        """设置当前使用的工具"""
        # 如果之前在进行文本输入，取消输入状态
        if self.is_text_input and tool_name != "text_input":
            self.finishTextInput()
        
        # 设置当前工具
        self.current_tool = tool_name
        print(f"已选择工具: {tool_name}")
        
        # 根据工具类型设置特定属性
        if tool_name == "text_input":
            self.is_text_input = True
            self.current_text = ""
            
            # 设置文本光标闪烁
            if self.text_cursor_timer is None:
                self.text_cursor_timer = QTimer(self)
                self.text_cursor_timer.timeout.connect(self.toggleTextCursor)
            if not self.text_cursor_timer.isActive():
                self.text_cursor_timer.start(500)
        
        # 如果选择了马赛克工具，显示大小选择器
        elif tool_name == "mosaic":
            # 让用户选择马赛克大小
            mosaic_size, ok = QInputDialog.getInt(
                self, "马赛克大小", "请选择马赛克块大小 (像素):", 
                self.mosaic_size, 2, 50, 1
            )
            if ok:
                self.mosaic_size = mosaic_size
                print(f"设置马赛克大小: {mosaic_size}")
    
    def setColor(self):
        """设置画笔颜色"""
        color = QColorDialog.getColor(self.pen_color, self)
        if color.isValid():
            self.pen_color = color
            
            # 更新颜色按钮图标
            color_pixmap = QPixmap(24, 24)
            color_pixmap.fill(self.pen_color)
            self.color_action.setIcon(QIcon(color_pixmap))
            
            print(f"设置颜色: {color.name()}")
    
    def setFont(self):
        """设置文本字体"""
        font, ok = QFontDialog.getFont(self.text_font, self)
        if ok:
            self.text_font = font
            print(f"设置字体: {font.family()} {font.pointSize()}")
    
    def eventFilter(self, source, event):
        """事件过滤器，用于处理鼠标事件"""
        if source == self.image_label:
            # 如果正在输入文本，不处理鼠标事件
            if self.is_text_input and event.type() in [event.MouseButtonPress, event.MouseMove, event.MouseButtonRelease]:
                # 仅设置文本起始位置
                if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                    self.start_point = event.pos()
                    self.updateImageLabel()
                return True
            
            # 处理鼠标按下事件
            if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                # 检查是否点击了已有形状
                shape_index = self.getShapeAtPosition(event.pos())
                if shape_index >= 0:
                    # 开始移动形状，所有形状都可以移动
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
                if self.is_moving_shape and self.moving_shape_index >= 0:
                    # 移动形状
                    self.moveShape(event.pos())
                    return True
                elif self.is_drawing:
                    # 正常绘制
                    self.drawing(event.pos())
                    return True
                
            # 处理鼠标释放事件
            elif event.type() == event.MouseButtonRelease and event.button() == Qt.LeftButton:
                if self.is_moving_shape:
                    # 完成移动形状
                    self.finishMoveShape()
                    return True
                elif self.is_drawing:
                    # 完成绘制
                    self.endDrawing(event.pos())
                    return True
        
        return super().eventFilter(source, event)
    
    def mousePressEvent(self, event):
        """处理鼠标按下事件，支持拖动窗口"""
        if event.button() == Qt.LeftButton:
            # 如果点击在工具栏之外的区域，允许拖动窗口
            if not self.toolbar.geometry().contains(event.pos()):
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """处理鼠标移动事件，支持拖动窗口"""
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def startDrawing(self, pos):
        """开始绘制"""
        if not self.current_tool:
            return
        
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
            self.current_text = ""
            self.is_drawing = False
            
            # 确保文本光标闪烁
            if self.text_cursor_timer is None:
                self.text_cursor_timer = QTimer(self)
                self.text_cursor_timer.timeout.connect(self.toggleTextCursor)
            if not self.text_cursor_timer.isActive():
                self.text_cursor_timer.start(500)
            
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
            painter.drawText(self.start_point, text_to_draw)
            
            # 计算光标位置
            if self.text_cursor_visible:
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
        arrow_size = 15  # 箭头大小
        angle = 30  # 箭头角度（度）
        
        # 计算线段角度
        line_length = ((end.x() - start.x())**2 + (end.y() - start.y())**2)**0.5
        if line_length == 0:
            return
        
        # 计算单位向量
        dx = (end.x() - start.x()) / line_length
        dy = (end.y() - start.y()) / line_length
        
        # 计算箭头两边的点
        angle_rad = angle * 3.14159 / 180.0  # 转换为弧度
        
        # 计算箭头两翼的点
        x1 = end.x() - arrow_size * (dx * 3.14159/180.0 + dy * 3.14159/180.0)
        y1 = end.y() - arrow_size * (dy * 3.14159/180.0 - dx * 3.14159/180.0)
        
        x2 = end.x() - arrow_size * (dx * 3.14159/180.0 - dy * 3.14159/180.0)
        y2 = end.y() - arrow_size * (dy * 3.14159/180.0 + dx * 3.14159/180.0)
        
        # 绘制箭头
        painter.drawLine(end, QPoint(int(x1), int(y1)))
        painter.drawLine(end, QPoint(int(x2), int(y2)))
    
    def applyMosaic(self, shape):
        """应用马赛克效果到图像"""
        # 获取选定区域
        rect = QRect(shape["start"], shape["end"]).normalized()
        size = shape["size"]
        
        # 创建一个临时QImage用于处理
        image = self.current_pixmap.toImage()
        
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
                        if rect.contains(px, py):
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
                            if rect.contains(px, py):
                                image.setPixel(px, py, avg_color.rgb())
        
        # 更新当前pixmap
        self.current_pixmap = QPixmap.fromImage(image)
    
    def undo(self):
        """撤销上一步操作"""
        if self.shapes:
            self.shapes.pop()
            # 对于马赛克，需要重新加载原始图像并重新应用所有操作
            if any(shape["type"] == "mosaic" for shape in self.shapes):
                self.current_pixmap = QPixmap(self.original_pixmap)
                for shape in self.shapes:
                    if shape["type"] == "mosaic":
                        self.applyMosaic(shape)
            self.updateImageLabel()
            print("撤销上一步操作")
    
    def clearAll(self):
        """清除所有绘制内容"""
        self.shapes = []
        self.current_pixmap = QPixmap(self.original_pixmap)
        self.updateImageLabel()
        print("清除所有内容")
    
    def saveImage(self):
        """保存编辑后的图像并关闭编辑器"""
        # 获取当前显示的图像
        if self.current_pixmap:
            # 发出信号，通知截图编辑完成
            self.editingFinished.emit(self.current_pixmap)
            print("图像编辑完成")
            self.close()
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 退出编辑器
        if event.key() == Qt.Key_Escape:
            # 如果正在输入文本，先取消输入
            if self.is_text_input:
                self.finishTextInput()
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
        if self.is_text_input and self.current_text:
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
        
        # 重置文本输入状态
        self.is_text_input = False
        self.current_text = ""
        
        # 停止光标闪烁
        if self.text_cursor_timer:
            self.text_cursor_timer.stop()
        
        self.updateImageLabel()
    
    def getShapeAtPosition(self, pos):
        """检查指定位置是否有形状，返回形状索引"""
        # 从后向前检查，以便后绘制的形状优先
        for i in range(len(self.shapes)-1, -1, -1):
            shape = self.shapes[i]
            if shape["type"] in ["rectangle", "roi", "circle"]:
                rect = QRect(shape["start"], shape["end"]).normalized()
                if rect.contains(pos):
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
        size = 6
        pen = QPen(color, 1)
        painter.setPen(pen)
        painter.setBrush(QBrush(color))
        
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

def edit_screenshot(pixmap):
    """创建并显示截图编辑器"""
    editor = ScreenshotEditor(pixmap)
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