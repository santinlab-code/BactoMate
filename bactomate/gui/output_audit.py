"""A background, read-only generated-file report available from the File menu."""
from PyQt6.QtCore import QThread,pyqtSignal
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QPushButton,QFileDialog
from bactomate.modules.output_audit import audit_outputs


class AuditWorker(QThread):
    ready=pyqtSignal(object);failed=pyqtSignal(str);progress=pyqtSignal(str)
    def __init__(self,root,parent):super().__init__(parent);self.root=root
    def run(self):
        try:self.ready.emit(audit_outputs(self.root,self.progress.emit))
        except Exception as exc:self.failed.emit(str(exc))


class OutputAuditDialog(QDialog):
    def __init__(self,parent,root):
        super().__init__(parent);self.setWindowTitle('Generated files — read-only audit');self.resize(1100,650)
        layout=QVBoxLayout(self);self.status=QLabel('Inspecting generated files…');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['File','Purpose','Size (KiB)','Same bytes','Same table'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);layout.addWidget(self.table)
        save=QPushButton('Save report…');save.clicked.connect(self.save);layout.addWidget(save);self.report=None
        self.worker=AuditWorker(root,self);self.worker.ready.connect(self.receive);self.worker.failed.connect(self.status.setText)
        self.worker.progress.connect(self.status.setText);self.worker.start()
    def receive(self,report):
        self.report=report;self.table.setRowCount(len(report['files']))
        for row,item in enumerate(report['files']):
            for col,value in enumerate([item['path'],item['role'],round(item['size_bytes']/1024,1),'\n'.join(item['same_content']),'\n'.join(item['same_table'])]):self.table.setItem(row,col,QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents();self.table.resizeRowsToContents()
        count=sum(bool(item['same_content'] or item['same_table']) for item in report['files'])
        self.status.setText(f"{len(report['files'])} generated files · {count} files with matching content.\n"+'\n'.join(report['notes']+report['issues']))
    def save(self):
        if self.report is None:return
        path,_=QFileDialog.getSaveFileName(self,'Save audit report','bactomate-output-audit.json','JSON (*.json)')
        if path:
            from pathlib import Path
            import json
            Path(path).write_text(json.dumps(self.report,indent=2),encoding='utf8')
    def closeEvent(self,event):
        if self.worker.isRunning():event.ignore();return
        super().closeEvent(event)
    def reject(self):
        if not self.worker.isRunning():super().reject()
