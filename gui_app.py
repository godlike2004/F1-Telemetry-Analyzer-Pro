import sys
import os
import webbrowser
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QMessageBox


class App(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("🏎️ F1 Telemetry Analyzer PRO")
        self.setGeometry(200, 200, 400, 300)

        layout = QVBoxLayout()

        title = QLabel("F1 Telemetry Analyzer", self)
        layout.addWidget(title)

        btn1 = QPushButton("Run Analysis")
        btn1.clicked.connect(self.run_analysis)
        layout.addWidget(btn1)

        btn2 = QPushButton("Open Dashboard")
        btn2.clicked.connect(self.open_dashboard)
        layout.addWidget(btn2)

        btn3 = QPushButton("Open CSV Folder")
        btn3.clicked.connect(self.open_folder)
        layout.addWidget(btn3)

        self.setLayout(layout)

    def run_analysis(self):
        os.system("python main.py")
        QMessageBox.information(self, "Done", "Analysis Complete!")

    def open_dashboard(self):
        webbrowser.open("http://localhost:8501")
        os.system("streamlit run app.py")

    def open_folder(self):
        os.startfile("data")


app = QApplication(sys.argv)
window = App()
window.show()
sys.exit(app.exec_())