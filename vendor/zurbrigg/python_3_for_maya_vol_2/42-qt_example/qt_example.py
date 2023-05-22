from PySide2 import QtWidgets

class ExampleDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(ExampleDialog, self).__init__(parent)

        self.setWindowTitle("Qt Example")
        self.setMinimumWidth(300)

        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.lineedit = QtWidgets.QLineEdit()
        self.checkbox = QtWidgets.QCheckBox()
        self.ok_btn = QtWidgets.QPushButton("OK")

    def create_layout(self):
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Name:", self.lineedit)
        form_layout.addRow("Hidden:", self.checkbox)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(button_layout)


if __name__ == "__main__":

    example_dialog = ExampleDialog()
    example_dialog.show()
