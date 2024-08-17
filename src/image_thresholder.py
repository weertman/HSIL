import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QSlider, QFileDialog, QGraphicsView, QGraphicsScene)
from PySide6.QtGui import QPixmap, QImage, QWheelEvent, QTransform, QMouseEvent
from PySide6.QtCore import Qt, QPointF, QPoint
import cv2
import numpy as np


class CustomGraphicsView(QGraphicsView):
    def __init__(self, parent=None, main_app=None):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._zoom = 0
        self._empty = True
        self._pan = False
        self._panStart = QPoint()
        self.set_thresholds_from_click = False
        self.main_app = main_app  # Reference to the main application

    def wheelEvent(self, event):
        if not self._empty:
            factor = 1.15
            if event.angleDelta().y() > 0:
                self._zoom += 1
                self.scale(factor, factor)
            elif event.angleDelta().y() < 0:
                self._zoom -= 1
                self.scale(1 / factor, 1 / factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = True
            self.setCursor(Qt.ClosedHandCursor)
            self._panStart = event.position().toPoint()
        elif event.button() == Qt.LeftButton and self.set_thresholds_from_click and not self._empty:
            scene_pos = self.mapToScene(event.position().toPoint())
            if self.main_app:  # Make sure we have the main app reference
                self.main_app.set_thresholds_from_pixel(int(scene_pos.x()), int(scene_pos.y()))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan:
            delta = event.position().toPoint() - self._panStart
            self._panStart = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)


class ImageProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Main widget
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)

        # Image viewers with custom graphics view
        self.input_viewer = CustomGraphicsView(parent=self, main_app=self)
        self.output_viewer = CustomGraphicsView(parent=self, main_app=self)

        image_layout = QHBoxLayout()
        image_layout.addWidget(self.input_viewer)
        image_layout.addWidget(self.output_viewer)

        layout.addLayout(image_layout)

        # Load buttons
        button_layout = QHBoxLayout()
        load_button = QPushButton('Load Image')
        save_button = QPushButton('Save Image')
        toggle_nan_button = QPushButton('Toggle NaN Highlight')
        pixel_threshold_button = QPushButton('Toggle Pixel Threshold')
        reset_button = QPushButton('Reset Thresholds')

        load_button.clicked.connect(self.load_image)
        save_button.clicked.connect(self.save_image)
        toggle_nan_button.clicked.connect(self.toggle_nan_highlight)
        pixel_threshold_button.clicked.connect(self.toggle_pixel_threshold)
        reset_button.clicked.connect(self.reset_thresholds)

        button_layout.addWidget(load_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(toggle_nan_button)
        button_layout.addWidget(pixel_threshold_button)
        button_layout.addWidget(reset_button)
        layout.addLayout(button_layout)

        # Sliders for adjusting the range of transparency
        self.lower_red_slider = self.create_slider()
        self.upper_red_slider = self.create_slider(255)
        self.lower_green_slider = self.create_slider()
        self.upper_green_slider = self.create_slider(255)
        self.lower_blue_slider = self.create_slider()
        self.upper_blue_slider = self.create_slider(255)

        slider_layout = QVBoxLayout()
        self.add_slider_group(slider_layout, "Red", self.lower_red_slider, self.upper_red_slider)
        self.add_slider_group(slider_layout, "Green", self.lower_green_slider, self.upper_green_slider)
        self.add_slider_group(slider_layout, "Blue", self.lower_blue_slider, self.upper_blue_slider)

        layout.addLayout(slider_layout)

        self.setWindowTitle('Image Transparency Processor')
        self.setGeometry(100, 100, 800, 600)

        self.input_image_path = None
        self.processed_image = None
        self.output_image = None
        self.highlight_nan = False

    def create_slider(self, initial_value=0):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(initial_value)
        slider.valueChanged.connect(self.process_image)
        return slider

    def add_slider_group(self, layout, label, lower_slider, upper_slider):
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel(f"{label} Lower:"))
        hbox.addWidget(lower_slider)
        hbox.addWidget(QLabel(f"{label} Upper:"))
        hbox.addWidget(upper_slider)
        layout.addLayout(hbox)

    def load_image(self):
        self.input_image_path, _ = QFileDialog.getOpenFileName(self, "Open Image File")
        if self.input_image_path:
            self.display_image(self.input_image_path, self.input_viewer)
            self.process_image()

    def save_image(self):
        if self.processed_image is not None:
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Image File",
                                                       filter="Image Files (*.png *.jpg *.bmp)")

            if save_path:
                if not (save_path.endswith('.png') or save_path.endswith('.jpg') or save_path.endswith('.bmp')):
                    save_path += '.png'  # Default to .png if no extension is provided

                image_bgr = cv2.cvtColor(self.processed_image, cv2.COLOR_RGBA2BGRA)
                cv2.imwrite(save_path, image_bgr)

    def display_image(self, path, view):
        image = cv2.imread(path)

        # Fix image rotation
        # Check if the image's EXIF data has orientation info, if available. If not, only rotate images when they are upside down.
        if image.shape[0] < image.shape[1]:  # Rotate back if portrait orientation
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Convert and display the image without reducing resolution
        q_image = self.convert_cv_qt(image)
        scene = QGraphicsScene()
        scene.addPixmap(q_image)
        view.setScene(scene)
        view._empty = False

    def convert_cv_qt(self, cv_img):
        """Convert from an OpenCV image to QPixmap."""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = QPixmap.fromImage(convert_to_Qt_format)
        return p

    def process_image(self):
        if not self.input_image_path:
            return

        image = cv2.imread(self.input_image_path)
        image_rgba = cv2.cvtColor(image, cv2.COLOR_BGR2RGBA)

        lower_red = self.lower_red_slider.value()
        upper_red = self.upper_red_slider.value()
        lower_green = self.lower_green_slider.value()
        upper_green = self.upper_green_slider.value()
        lower_blue = self.lower_blue_slider.value()
        upper_blue = self.upper_blue_slider.value()

        lower_bound = np.array([lower_blue, lower_green, lower_red, 0])
        upper_bound = np.array([upper_blue, upper_green, upper_red, 255])
        mask = cv2.inRange(image_rgba, lower_bound, upper_bound)

        image_rgba[mask != 0] = [0, 0, 0, 0]

        self.processed_image = image_rgba.copy()

        if self.highlight_nan:
            nan_highlight = np.zeros_like(image_rgba)
            nan_highlight[mask != 0] = [255, 0, 0, 255]
            image_rgba = cv2.addWeighted(image_rgba, 1.0, nan_highlight, 0.5, 0)

        height, width, channel = image_rgba.shape
        bytes_per_line = 4 * width
        q_img = QImage(image_rgba.data, width, height, bytes_per_line, QImage.Format_RGBA8888)

        output_pixmap = QPixmap.fromImage(q_img)
        scene = QGraphicsScene()
        scene.addPixmap(output_pixmap)
        self.output_viewer.setScene(scene)
        self.output_viewer._empty = False

    def toggle_nan_highlight(self):
        self.highlight_nan = not self.highlight_nan
        self.process_image()

    def toggle_pixel_threshold(self):
        self.input_viewer.set_thresholds_from_click = not self.input_viewer.set_thresholds_from_click
        if self.input_viewer.set_thresholds_from_click:
            self.statusBar().showMessage("Click on the image to set thresholds.")
        else:
            self.statusBar().clearMessage()

    def reset_thresholds(self):
        self.lower_red_slider.setValue(0)
        self.upper_red_slider.setValue(255)
        self.lower_green_slider.setValue(0)
        self.upper_green_slider.setValue(255)
        self.lower_blue_slider.setValue(0)
        self.upper_blue_slider.setValue(255)
        self.process_image()

    def set_thresholds_from_pixel(self, x, y):
        image = cv2.imread(self.input_image_path)
        if image is not None:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            if 0 <= x < image_rgb.shape[1] and 0 <= y < image_rgb.shape[0]:
                pixel_color = image_rgb[y, x]
                self.lower_red_slider.setValue(pixel_color[0])
                self.upper_red_slider.setValue(pixel_color[0])
                self.lower_green_slider.setValue(pixel_color[1])
                self.upper_green_slider.setValue(pixel_color[1])
                self.lower_blue_slider.setValue(pixel_color[2])
                self.upper_blue_slider.setValue(pixel_color[2])
                self.process_image()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageProcessorApp()
    ex.show()
    sys.exit(app.exec())
