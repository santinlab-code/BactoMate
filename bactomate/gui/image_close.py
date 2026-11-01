"""Explicit Save / Discard / Cancel for image-window close buttons."""
from PyQt6.QtWidgets import QMessageBox,QFileDialog


def close_choice(parent):
    return QMessageBox.question(parent,'Close image','Save this image before closing?',
        QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel)


def save_canvas_image(parent,canvas):
    path,_=QFileDialog.getSaveFileName(parent,'Save displayed image','','TIFF (*.tif);;JPEG (*.jpg)')
    if not path:return False
    try:
        from PIL import Image
        from PyQt6.QtGui import QImage
        image=canvas._pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        value=Image.frombytes('RGBA',(image.width(),image.height()),image.bits().asstring(image.sizeInBytes()),'raw','RGBA',image.bytesPerLine())
        value.convert('RGB').save(path)
        return True
    except Exception as exc:
        QMessageBox.warning(parent,'Cannot save image',str(exc));return False
