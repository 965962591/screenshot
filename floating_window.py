from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout, QPushButton, QMenu, QAction
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap, QImage, QCursor, QIcon
import os

class FloatingWindow(QWidget):
    def __init__(self, image_path=None, pixmap=None):
        super().__init__()
        self.initUI(image_path, pixmap)
        
    def initUI(self, image_path=None, pixmap=None):
        # 设置窗口标志
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建图片标签
        self.image_label = QLabel()
        
        valid_image = False
        
        # 尝试从文件路径加载
        if image_path and os.path.exists(image_path):
            try:
                print(f"从文件加载图像: {image_path}")
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    valid_image = True
                    print(f"成功从文件加载图像: {pixmap.width()}x{pixmap.height()}")
            except Exception as e:
                print(f"从文件加载图像失败: {e}")
        
        # 如果提供了pixmap对象
        if not valid_image and pixmap is not None:
            try:
                if not pixmap.isNull():
                    valid_image = True
                    print(f"使用提供的QPixmap: {pixmap.width()}x{pixmap.height()}")
                else:
                    print("提供的QPixmap对象为空")
            except Exception as e:
                print(f"使用QPixmap对象时出错: {e}")
        
        # 如果没有有效图像，创建默认图像
        if not valid_image:
            print("未能加载有效图像，创建默认图像")
            pixmap = QPixmap(300, 200)
            pixmap.fill(Qt.red)
        
        # 设置图像和调整窗口大小
        self.image_label.setPixmap(pixmap)
        self.resize(pixmap.width(), pixmap.height())
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        
        # 用于跟踪鼠标移动
        self.dragging = False
        self.offset = QPoint()
        
        # 显示窗口
        self.show()
        self.activateWindow()
        self.raise_()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
        elif event.button() == Qt.RightButton:
            self.showContextMenu(event.pos())
    
    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.mapToParent(event.pos() - self.offset))
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def showContextMenu(self, position):
        menu = QMenu(self)
        
        # 添加保存选项
        saveAction = QAction("保存图像", self)
        saveAction.triggered.connect(self.saveImage)
        menu.addAction(saveAction)
        
        # 添加关闭选项
        closeAction = QAction("关闭窗口", self)
        closeAction.triggered.connect(self.close)
        menu.addAction(closeAction)
        
        # 显示菜单
        menu.exec_(self.mapToGlobal(position))
    
    def saveImage(self):
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 确保输出目录存在
            if not os.path.exists("output"):
                os.makedirs("output")
                
            # 保存文件
            filename = f"output/floating_saved_{timestamp}.png"
            pixmap = self.image_label.pixmap()
            if pixmap and not pixmap.isNull():
                pixmap.save(filename)
                print(f"图像已保存至: {filename}")
        except Exception as e:
            print(f"保存图像时出错: {e}")

def create_floating_window(image_path=None, pixmap=None):
    """
    创建一个新的悬浮窗口
    :param image_path: 图片文件路径
    :param pixmap: QPixmap对象
    :return: FloatingWindow实例
    """
    try:
        window = FloatingWindow(image_path, pixmap)
        return window
    except Exception as e:
        print(f"创建浮动窗口失败: {e}")
        return None

if __name__ == "__main__":
    # 测试代码
    import sys
    app = QApplication(sys.argv)
    # 创建一个测试用的空白图片
    test_pixmap = QPixmap(300, 200)
    test_pixmap.fill(Qt.red)
    window = create_floating_window(pixmap=test_pixmap)
    sys.exit(app.exec_()) 