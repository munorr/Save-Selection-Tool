import maya.cmds as cmds
from maya import OpenMayaUI as omui

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import QTimer, QPropertyAnimation, QEasingCurve
    from PySide6.QtGui import QColor
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import QTimer, QPropertyAnimation, QEasingCurve
    from PySide2.QtGui import QColor
    from shiboken2 import wrapInstance

import json

def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)

def hex_value(hex_color, factor):
    color = QColor(hex_color)
    h, s, v, a = color.getHsvF()
    v = min(max(v * factor, 0), 1) 
    color.setHsvF(h, s, v, a)
    return color.name()

class CustomDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, title="", size=(250, 150)):
        super(CustomDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(*size)
        self.setStyleSheet('''
            QDialog {
                background-color: rgba(40, 40, 40, 0.9);
                border-radius: 5px;
            }
            QLabel, QRadioButton {
                color: white;
            }
            QLineEdit, QComboBox {
                background-color: #4d4d4d;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton {
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton#acceptButton {
                background-color: #00749a;
            }
            QPushButton#acceptButton:hover {
                background-color: #00ade6;
            }
            QPushButton#closeButton {
                background-color: #a30000;
            }
            QPushButton#closeButton:hover {
                background-color: #ff0000;
            }
        ''')
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # Add Enter key shortcut
        self.enter_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Return), self)
        self.enter_shortcut.activated.connect(self.accept)

    def add_widget(self, widget):
        self.layout.addWidget(widget)

    def add_button_box(self):
        button_layout = QtWidgets.QHBoxLayout()
        accept_button = QtWidgets.QPushButton("Accept")
        close_button = QtWidgets.QPushButton("Close")
        accept_button.setObjectName("acceptButton")
        close_button.setObjectName("closeButton")
        #accept_button.setFixedWidth(80)
        #close_button.setFixedWidth(80)
        button_layout.addWidget(accept_button)
        button_layout.addWidget(close_button)
        self.layout.addStretch()
        self.layout.addLayout(button_layout)
        accept_button.clicked.connect(self.accept)
        close_button.clicked.connect(self.reject)
        return accept_button, close_button
    
class DraggableButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super(DraggableButton, self).__init__(text, parent)
        self.setStyleSheet('''
            QPushButton {background-color: #4d4d4d;color: white;border-radius: 3px;padding: 2px;}
            QPushButton:hover {background-color: #5a5a5a;}
            QToolTip {background-color: #5285a6;color: white;border: 0px;}
        ''')
        self.setFixedHeight(22)
        self.setToolTip("Select Sets")
        self.setFixedWidth(self.calculate_button_width(text))

    def calculate_button_width(self, text, padding=20):
        font_metrics = QtGui.QFontMetrics(QtWidgets.QApplication.font())
        text_width = font_metrics.horizontalAdvance(text)
        return text_width + padding

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            self.drag_start_position = event.pos()
        super(DraggableButton, self).mousePressEvent(event)
        

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.MiddleButton:
            if (event.pos() - self.drag_start_position).manhattanLength() < QtWidgets.QApplication.startDragDistance():
                return
            drag = QtGui.QDrag(self)
            mime_data = QtCore.QMimeData()
            mime_data.setText(self.text())
            drag.setMimeData(mime_data)
            drag.exec_(QtCore.Qt.MoveAction)

class ColorButton(QtWidgets.QPushButton):
    def __init__(self, color, parent=None):
        super(ColorButton, self).__init__(parent)
        self.setFixedSize(20, 20)
        self.setStyleSheet(f"background-color: {color}; border: none; border-radius: 3px;")

class TabButton(QtWidgets.QPushButton):
    tab_clicked = QtCore.Signal(str)

    def __init__(self, text, parent=None):
        super(TabButton, self).__init__(text, parent)
        self.tab_name = text
        self.setStyleSheet('''
        QPushButton {background-color: #4d4d4d;color: white;border-radius: 8px;padding: 1px;}
        QPushButton:hover {background-color: #5a5a5a;}
        QToolTip {background-color: #5285a6;color: white;border: 0px;}
        ''')
        self.setFixedHeight(16)
        self.setFixedWidth(self.calculate_button_width(text))
        self.setToolTip('Select Tab')
        self.clicked.connect(self.on_clicked)

    def calculate_button_width(self, text, padding=10):
        font_metrics = QtGui.QFontMetrics(QtWidgets.QApplication.font())
        text_width = font_metrics.horizontalAdvance(text)
        return text_width + padding

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super(TabButton, self).mousePressEvent(event)

    def on_clicked(self):
        self.tab_clicked.emit(self.tab_name)

class SelectSetToolWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SelectSetToolWindow, self).__init__(maya_main_window(), QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setWindowTitle("SelectSetTool")
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        
        self.setStyleSheet('''
            QWidget {background-color: rgba(0, 0, 0, 0);}
            QDialog, QMessageBox {background-color: #444444 ;color: #222222;}
            QLabel {color: #ffffff;}
            QLineEdit {background-color: #333333;color: #ffffff;border: 0px solid #555555; padding: 2px;}
            QPushButton {background-color: #333333;color: white;border-radius: 3px;padding: 5px;}
            QPushButton:hover {background-color: #5a5a5a;}
        ''')
        self.tabs = {}
        self.current_tab = None
        self.setup_ui()
        
        self.setup_connections()

        self.populate_existing_selections()
        # Check if there are no tabs and add a default one if necessary
        if not self.tabs:
            self.add_tab("1")
        
        self.color_palette = [
            "#4d4d4d", "#d58c09", "#16aaa6", "#9416ca", 
            "#873b75", "#6c9809", "#314d79", "#cf2222"
        ]

        self.setWindowOpacity(1)
        self.fade_timer = QTimer(self)
        self.fade_timer.setSingleShot(True)
        self.fade_timer.timeout.connect(self.start_fade_animation)
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(1000)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_frame_context_menu)
        self.fade_away_enabled = False

        self.context_menu_open = False

    def setup_ui(self):
        self.mainLayout = QtWidgets.QHBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        self.frame = QtWidgets.QFrame(self)
        self.frame.setStyleSheet('''
            QFrame {
                border: 0px solid gray;
                border-radius: 5px;
                background-color: rgba(40, 40, 40, .6);
            }
        ''')
        flm = 7 #frame layout margin
        frameLayout = QtWidgets.QVBoxLayout(self.frame)
        frameLayout.setContentsMargins(flm, flm, flm, flm)
        frameLayout.setSpacing(5)

        topFrameLayout = QtWidgets.QHBoxLayout()
        topFrameLayout.setAlignment(QtCore.Qt.AlignTop)
        self.setup_save_button(topFrameLayout)

        tabFrame = QtWidgets.QFrame()
        #tabFrameLayout = QtWidgets.QHBoxLayout(tabFrame)
        tabFrame.setStyleSheet("QFrame { border: 0px solid gray; border-radius: 12px; background-color: rgba(30, 30, 30, .6); }")
        tabFrame.setFixedHeight(24)


        self.tabLayout = QtWidgets.QHBoxLayout(tabFrame)
        self.tabLayout.setContentsMargins(4, 4, 4, 4)
        self.tabLayout.setSpacing(4)
        topFrameLayout.addWidget(tabFrame)

        topFrameLayout.addStretch()

        self.setup_close_button(topFrameLayout)
        frameLayout.addLayout(topFrameLayout)

        self.addTabButton = QtWidgets.QPushButton("+")
        self.addTabButton.setFixedSize(16,16)
        self.addTabButton.setStyleSheet('''
            QPushButton {background-color: #76a507; color: white; border-radius: 8px; padding:0px 0px 1px 0px;}
            QPushButton:hover {background-color: #91cb08;}
            QToolTip {background-color: #7fb20a; color: white; border: 0px;}''')
        
        self.addTabButton.setToolTip('Add new tab')
        
        self.tabLayout.addWidget(self.addTabButton)

        sblm = 6 # selectionButtonsLayout margin
        selectionButtonsFrame = QtWidgets.QFrame()
        selectionButtonsFrame.setStyleSheet("QFrame { border: 0px solid gray; border-radius: 3px; background-color: rgba(30, 30, 30, .6); }")
        selectionButtonsFrame.setFixedHeight(34)
        self.selectionButtonsLayout = QtWidgets.QHBoxLayout(selectionButtonsFrame)
        self.selectionButtonsLayout.setContentsMargins(sblm, sblm, sblm, sblm)
        self.selectionButtonsLayout.setSpacing(sblm)
        self.selectionButtonsLayout.setAlignment(QtCore.Qt.AlignLeft)
        frameLayout.addWidget(selectionButtonsFrame)
        

        self.mainLayout.addWidget(self.frame)
        self.mainLayout.addStretch()

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def setup_save_button(self, layout):
        color = '#006180'
        self.saveSelectionButton = QtWidgets.QPushButton("Save Selection", self)
        self.saveSelectionButton.setStyleSheet(f'''
            QPushButton{{background-color: {color};border-radius: 3px;}}
            QPushButton:hover {{background-color: {hex_value(color, 1.2)} ;}}
            QPushButton:pressed {{background-color: {hex_value(color, 0.8)} ;}}
            QToolTip {{background-color: {color};color: white; border:0px;}}
        ''')
        self.saveSelectionButton.setFixedSize(85, 20)
        self.saveSelectionButton.setToolTip("Save Selected Object")
        self.saveSelectionButton.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.saveSelectionButton.customContextMenuRequested.connect(self.show_save_button_context_menu)
        layout.addWidget(self.saveSelectionButton)

    def show_save_button_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet('''
            QMenu {
                background-color: rgba(30, 30, 30, .7);
                border-radius: 3px;
                padding: 0px 3px 0px 3px;
            }
            QMenu::item {
                background-color: #00749a;
                padding: 3px 20px 3px 5px;
                margin: 3px 0px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #00ade6;
            }
        ''')

        store_action = menu.addAction("Store Selection Data")
        load_action = menu.addAction("Load Selection Data")

        action = menu.exec_(self.saveSelectionButton.mapToGlobal(pos))

        if action == store_action:
            self.store_selection_data()
        elif action == load_action:
            self.load_selection_data()

    def store_selection_data(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Selection Data", "", "JSON Files (*.json)")
        if file_path:
            selection_dict = self.get_selection_dict()
            with open(file_path, 'w') as f:
                json.dump(selection_dict, f)
            cmds.inViewMessage(amg=f"Selection data saved to {file_path}", pos='midCenter', fade=True)

    def load_selection_data(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Selection Data", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'r') as f:
                loaded_data = json.load(f)
            
            dialog = CustomDialog(self, "Load Options", (200, 130))
            dialog.add_widget(QtWidgets.QLabel("Choose load option:"))
            overwrite_radio = QtWidgets.QRadioButton("Overwrite existing data")
            add_radio = QtWidgets.QRadioButton("Add to existing data")
            overwrite_radio.setChecked(True)
            dialog.add_widget(overwrite_radio)
            dialog.add_widget(add_radio)
            dialog.add_button_box()

            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                if overwrite_radio.isChecked():
                    self.save_selection_dict(loaded_data)
                else:
                    current_data = self.get_selection_dict()
                    new_data = self.merge_selection_data(current_data, loaded_data)
                    self.save_selection_dict(new_data)

                self.refresh_ui()
                cmds.inViewMessage(amg="Selection data loaded successfully", pos='midCenter', fade=True)

    def refresh_ui(self):
        # Clear existing tabs and buttons
        for tab_name in list(self.tabs.keys()):
            for button in self.tabs[tab_name]:
                button.setParent(None)
                button.deleteLater()
            self.tabs[tab_name].clear()

        # Remove all tab buttons
        for i in reversed(range(self.tabLayout.count() - 1)):
            widget = self.tabLayout.itemAt(i).widget()
            if isinstance(widget, TabButton):
                self.tabLayout.removeWidget(widget)
                widget.deleteLater()

        # Clear the tabs dictionary
        self.tabs.clear()

        # Repopulate the UI
        self.populate_existing_selections()
        self.update_tab_buttons()
        self.update_selection_buttons()

    def merge_selection_data(self, current_data, new_data):
        merged_data = {'selections': current_data['selections'].copy(), 'tabs': current_data['tabs'].copy()}

        # Merge selections with '_new' suffix
        for name, selection in new_data['selections'].items():
            new_name = f"{name}_new"
            merged_data['selections'][new_name] = selection

        # Merge tabs with '_new' suffix
        for tab, selections in new_data['tabs'].items():
            new_tab_name = f"{tab}_new"
            if new_tab_name not in merged_data['tabs']:
                merged_data['tabs'][new_tab_name] = []
            for name in selections:
                new_name = f"{name}_new"
                merged_data['tabs'][new_tab_name].append(new_name)

        return merged_data

    def get_unique_name(self, name, existing_selections):
        unique_name = name
        counter = 1
        while unique_name in existing_selections:
            unique_name = f"{name}_{counter}"
            counter += 1
        return unique_name

    def create_selection_button(self, selection_name):
        button = DraggableButton(selection_name)
        button.clicked.connect(lambda: self.select_objects(selection_name, QtWidgets.QApplication.keyboardModifiers()))
        button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(lambda pos, btn=button: self.show_context_menu(pos, btn))

        # Set tooltip and color
        button.setToolTip(f"Select {selection_name} set")
        selection_dict = self.get_selection_dict()
        if selection_name in selection_dict['selections'] and 'color' in selection_dict['selections'][selection_name]:
            color = selection_dict['selections'][selection_name]['color']
            if color:
                self.set_button_color(button, color)

        return button

    def setup_close_button(self, layout):
        self.closeButton = QtWidgets.QPushButton('✕', self)
        self.closeButton.setStyleSheet('''
            QPushButton {background-color: rgba(200, 0, 0, 0.6); color: #ff9393; border: none; border-radius: 3px; padding: 0px 0px 2px 0px;}
            QPushButton:hover {background-color: rgba(255, 0, 0, 0.6);}
            QToolTip {background-color: rgba(200, 0, 0, 0.6); color: white; border: 0px;}''')
        
        self.closeButton.setToolTip('Close')
        self.closeButton.setFixedSize(18, 18)
        layout.addWidget(self.closeButton)

    def setup_connections(self):
        self.saveSelectionButton.clicked.connect(self.save_selection)
        self.addTabButton.clicked.connect(self.add_new_tab)
        self.closeButton.clicked.connect(self.close)
        self.oldPos = self.pos()
        self.frame.mousePressEvent = self.mousePressEvent
        self.frame.mouseMoveEvent = self.mouseMoveEvent
        self.setAcceptDrops(True)

    # Event handlers
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.oldPos = event.globalPos()
        maya_main_window().activateWindow()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            delta = QtCore.QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()
        maya_main_window().activateWindow()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        maya_main_window().activateWindow()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()
        maya_main_window().activateWindow()

    def dropEvent(self, event):
        source_button = event.source()
        target_position = self.selectionButtonsLayout.indexOf(self.childAt(event.pos()))
        if source_button and target_position != -1:
            self.selectionButtonsLayout.removeWidget(source_button)
            self.selectionButtonsLayout.insertWidget(target_position, source_button)
            
            # Update self.tabs for the current tab
            current_tab = self.current_tab
            self.tabs[current_tab].remove(source_button)
            self.tabs[current_tab].insert(target_position, source_button)
            
            # Update the selection dictionary
            self.update_database_order()

        event.acceptProposedAction()
        maya_main_window().activateWindow()

    def enterEvent(self, event):
        if self.fade_away_enabled:
            self.fade_timer.stop()
            self.fade_animation.stop()
            self.fade_animation.setDuration(100)  # 100ms for fade in
            self.fade_animation.setStartValue(self.windowOpacity())
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.start()
        super(SelectSetToolWindow, self).enterEvent(event)

    def leaveEvent(self, event):
        if self.fade_away_enabled and not self.context_menu_open:
            self.fade_timer.start(10)  # 10ms delay before fade out
        super(SelectSetToolWindow, self).leaveEvent(event)

    def start_fade_animation(self):
        if self.fade_away_enabled and not self.context_menu_open:
            self.fade_animation.setDuration(400)  # 1000ms for fade out
            self.fade_animation.setStartValue(self.windowOpacity())
            self.fade_animation.setEndValue(0.1)
            self.fade_animation.start()

    # Tab Functionality 
    def initialize_first_tab(self):
        if not self.tabs:
            first_tab_name = "1"
            tab_button = TabButton(first_tab_name)
            tab_button.clicked.connect(lambda: self.switch_tab(first_tab_name))
            tab_button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            tab_button.customContextMenuRequested.connect(lambda pos, btn=tab_button: self.show_tab_context_menu(pos, btn))
            
            self.tabLayout.insertWidget(self.tabLayout.count() - 1, tab_button)
            self.tabs[first_tab_name] = []
            self.switch_tab(first_tab_name)
            
            selection_dict = self.get_selection_dict()
            if first_tab_name not in selection_dict['tabs']:
                selection_dict['tabs'][first_tab_name] = []
            self.save_selection_dict(selection_dict)

    def add_tab(self, tab_name):
        selection_dict = self.get_selection_dict()
        # Check if the tab name already exists
        if tab_name in self.tabs:
            # If it exists, generate a unique name
            counter = 1
            while f"{tab_name}_{counter}" in self.tabs:
                counter += 1
            tab_name = f"{tab_name}_{counter}"

        tab_button = TabButton(tab_name)
        tab_button.tab_clicked.connect(self.switch_tab)
        tab_button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tab_button.customContextMenuRequested.connect(self.on_tab_context_menu_requested)
        self.tabLayout.insertWidget(self.tabLayout.count() - 1, tab_button)
        self.tabs[tab_name] = []

        if tab_name not in selection_dict['tabs']:
            selection_dict['tabs'][tab_name] = []
        self.save_selection_dict(selection_dict)
        self.switch_tab(tab_name)

    def add_new_tab(self):
        dialog = CustomDialog(self, "New Tab", (180, 100))
        dialog.add_widget(QtWidgets.QLabel("Enter tab name:"))
        input_field = QtWidgets.QLineEdit()
        dialog.add_widget(input_field)
        dialog.add_button_box()

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_tab_name = input_field.text()
            if new_tab_name:
                self.add_tab(new_tab_name)

    def rename_tab(self, button):
        old_name = button.text()
        dialog = CustomDialog(self, "Rename Tab", (180, 100))
        dialog.add_widget(QtWidgets.QLabel("Enter new tab name:"))
        input_field = QtWidgets.QLineEdit(old_name)
        dialog.add_widget(input_field)
        dialog.add_button_box()

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_name = input_field.text()
            if new_name and new_name != old_name:
                # Check if the new name already exists
                if new_name in self.tabs:
                    counter = 1
                    while f"{new_name}_{counter}" in self.tabs:
                        counter += 1
                    new_name = f"{new_name}_{counter}"

                selection_dict = self.get_selection_dict()
                selection_dict['tabs'][new_name] = selection_dict['tabs'].pop(old_name)
                self.save_selection_dict(selection_dict)

                # Update the tabs dictionary
                self.tabs[new_name] = self.tabs.pop(old_name)

                if self.current_tab == old_name:
                    self.current_tab = new_name

                # Update button text and width
                button.setText(new_name)
                button.setFixedWidth(button.calculate_button_width(new_name))

                # Reconnect the button's click event
                button.clicked.disconnect()
                button.clicked.connect(lambda: self.switch_tab(new_name))

                self.update_tab_buttons()
                self.update_selection_buttons()

    def delete_tab(self, button):
        tab_name = button.text()
        if len(self.tabs) == 1:
            QtWidgets.QMessageBox.warning(self, "Cannot Delete", "You must have at least one tab.")
            return

        dialog = CustomDialog(self, "Delete Tab", (200, 160))
        dialog.add_widget(QtWidgets.QLabel(f"Delete tab '{tab_name}'?"))
        delete_option = QtWidgets.QRadioButton("Delete tab and all buttons")
        move_option = QtWidgets.QRadioButton("Move buttons to another tab")
        delete_option.setChecked(True)
        dialog.add_widget(delete_option)
        dialog.add_widget(move_option)

        tab_combo = QtWidgets.QComboBox()
        for name in self.tabs.keys():
            if name != tab_name:
                tab_combo.addItem(name)
        dialog.add_widget(tab_combo)
        tab_combo.setVisible(False)

        accept_button, _ = dialog.add_button_box()

        def toggle_combo_visibility():
            tab_combo.setVisible(move_option.isChecked())
            dialog.adjustSize()

        delete_option.toggled.connect(toggle_combo_visibility)
        move_option.toggled.connect(toggle_combo_visibility)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selection_dict = self.get_selection_dict()
            if delete_option.isChecked():
                del selection_dict['tabs'][tab_name]
                del self.tabs[tab_name]
            else:
                target_tab = tab_combo.currentText()
                selection_dict['tabs'][target_tab].extend(selection_dict['tabs'][tab_name])
                del selection_dict['tabs'][tab_name]
                self.tabs[target_tab].extend(self.tabs[tab_name])
                del self.tabs[tab_name]

            self.save_selection_dict(selection_dict)
            self.tabLayout.removeWidget(button)
            button.deleteLater()

            if self.current_tab == tab_name:
                new_current_tab = next(iter(self.tabs))
                self.switch_tab(new_current_tab)
            else:
                self.update_tab_buttons()
                self.update_selection_buttons()

    def switch_tab(self, tab_name):
        if tab_name in self.tabs:
            self.current_tab = tab_name
            self.update_tab_buttons()
            self.update_selection_buttons()
        else:
            print(f"Error: Tab '{tab_name}' not found.")
    #----------------------------------------------------------------------------------------------------
    def on_tab_button_clicked(self, tab_name):
        self.switch_tab(tab_name)

    def on_tab_context_menu_requested(self, pos):
        button = self.sender()
        self.show_tab_context_menu(pos, button)

    def update_tab_buttons(self):
        # Remove all existing tab buttons
        for i in reversed(range(self.tabLayout.count() - 1)):
            widget = self.tabLayout.itemAt(i).widget()
            if isinstance(widget, TabButton):
                self.tabLayout.removeWidget(widget)
                widget.deleteLater()

        # Add tab buttons in the new order
        for tab_name in self.tabs.keys():
            tab_button = TabButton(tab_name)
            tab_button.tab_clicked.connect(self.switch_tab)
            tab_button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            tab_button.customContextMenuRequested.connect(self.on_tab_context_menu_requested)
            self.tabLayout.insertWidget(self.tabLayout.count() - 1, tab_button)

        # Update the styling
        for i in range(self.tabLayout.count() - 1):
            tab_button = self.tabLayout.itemAt(i).widget()
            if tab_button.text() == self.current_tab:
                tab_button.setStyleSheet('''
                QPushButton {
                    background-color: #5285a6;
                    color: white;
                    border-radius: 8px;
                    padding: 0px 0px 1px 0px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #6295b6;
                }
                QToolTip {
                    background-color: #5285a6;
                    color: white;
                    border: 0px;
                }
                ''')
            else:
                tab_button.setStyleSheet('''
                QPushButton {
                    background-color: #4d4d4d;
                    color: white;
                    border-radius: 8px;
                    padding: 0px 0px 1px 0px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #5a5a5a;
                }
                QToolTip {
                    background-color: #5285a6;
                    color: white;
                    border: 0px;
                }
                ''')
    
    def move_tab_left(self, button):
        tab_name = button.text()
        tab_index = self.get_tab_index(tab_name)
        if tab_index > 0:
            self.move_tab(tab_index, tab_index - 1)

    def move_tab_right(self, button):
        tab_name = button.text()
        tab_index = self.get_tab_index(tab_name)
        if tab_index < len(self.tabs) - 1:
            self.move_tab(tab_index, tab_index + 1)

    def get_tab_index(self, tab_name):
        return list(self.tabs.keys()).index(tab_name)

    def move_tab(self, old_index, new_index):
        tab_names = list(self.tabs.keys())
        tab_name = tab_names[old_index]

        # Update the tabs dictionary
        tab_names.insert(new_index, tab_names.pop(old_index))
        self.tabs = {name: self.tabs[name] for name in tab_names}

        # Update the database
        selection_dict = self.get_selection_dict()
        selection_dict['tabs'] = {name: selection_dict['tabs'][name] for name in tab_names}
        self.save_selection_dict(selection_dict)

        # Update the current_tab if it was moved
        if self.current_tab == tab_name:
            self.current_tab = tab_name

        # Update the UI
        self.update_tab_buttons()
    #----------------------------------------------------------------------------------------------------
    def show_tab_context_menu(self, pos, button):
        self.context_menu_open = True
        menu = QtWidgets.QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        menu.setStyleSheet('''
        QMenu {
            background-color: rgba(30, 30, 30,.7);
            border-radius: 3px;
            padding: 0px 3px 0px 3px;;
        }
        QMenu::item {
            background-color: #00749a;
            padding: 3px 20px 3px 5px;
            margin: 3px 0px;
            border-radius: 3px;
                        
        }
        QMenu::item:selected {
            background-color: #00ade6;
        }
        ''')

        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        move_left_action = menu.addAction("Move Left")
        move_right_action = menu.addAction("Move Right")

        action = menu.exec_(button.mapToGlobal(pos))
        self.context_menu_open = False
        if self.fade_away_enabled:
            self.fade_timer.start(10)
        if action == rename_action:
            self.rename_tab(button)
        elif action == delete_action:
            self.delete_tab(button)
        elif action == move_left_action:
            self.move_tab_left(button)
        elif action == move_right_action:
            self.move_tab_right(button)

    def move_button_to_tab(self, button, new_tab):
        selection_name = button.text()
        old_tab = self.current_tab

        # Update the selection_dict
        selection_dict = self.get_selection_dict()
        selection_dict['tabs'][old_tab].remove(selection_name)
        selection_dict['tabs'][new_tab].append(selection_name)
        self.save_selection_dict(selection_dict)

        # Update the self.tabs dictionary
        self.tabs[old_tab].remove(button)
        self.tabs[new_tab].append(button)

        # Update the UI
        self.selectionButtonsLayout.removeWidget(button)
        button.setParent(None)
        self.update_selection_buttons()

        # Show a message to confirm the move
        #cmds.inViewMessage(amg=f"Moved '{selection_name}' to tab '{new_tab}'", pos='midCenter', fade=True)

    # Select Button Functionality        
    def calculate_button_width(self, text, padding=20):
        font_metrics = QtGui.QFontMetrics(self.font())
        text_width = font_metrics.horizontalAdvance(text)
        return text_width + padding
    
    def add_selection_button(self, selection_name):
        button = DraggableButton(selection_name)
        button.clicked.connect(lambda: self.select_objects(selection_name, QtWidgets.QApplication.keyboardModifiers()))
        button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(lambda pos, btn=button: self.show_context_menu(pos, btn))

        # Set tooltip and color
        button.setToolTip(f"Select {selection_name} set")
        selection_dict = self.get_selection_dict()
        if selection_name in selection_dict['selections'] and 'color' in selection_dict['selections'][selection_name]:
            color = selection_dict['selections'][selection_name]['color']
            if color:
                self.set_button_color(button, color)

        # Add button to current tab
        self.tabs[self.current_tab].append(button)
        self.update_selection_buttons()

    def show_frame_context_menu(self, pos):
        self.context_menu_open = True
        menu = QtWidgets.QMenu(self)
        # Remove background and shadow
        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        menu.setStyleSheet('''
            QMenu {
                background-color: rgba(51, 51, 51, 0);
                border-radius: 3px;
                padding: 5px;
            }
            QMenu::item {
                background-color: #222222;
                padding: 6px ;
                border: 2px solid #00749a;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #111111;
            }''')
        
        toggle_fade_action = menu.addAction("Toggle Fade Away")
        toggle_fade_action.setCheckable(True)
        toggle_fade_action.setChecked(self.fade_away_enabled)
        
        action = menu.exec_(self.mapToGlobal(pos))
        self.context_menu_open = False
        if self.fade_away_enabled:
            self.fade_timer.start(10)
        if action == toggle_fade_action:
            self.toggle_fade_away()

    def toggle_fade_away(self):
        self.fade_away_enabled = not self.fade_away_enabled
        if not self.fade_away_enabled:
            self.fade_timer.stop()
            self.fade_animation.stop()
            self.setWindowOpacity(1.0)

    def show_context_menu(self, pos, button):
        self.context_menu_open = True
        menu = QtWidgets.QMenu()
        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        menu.setStyleSheet('''
            QMenu {
                background-color: rgba(30, 30, 30, .7);
                border-radius: 3px;
                padding: 0px 3px 0px 3px;
            }
            QMenu::item {
                background-color: #00749a;
                padding: 3px 20px 3px 5px;
                margin: 3px 0px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #00ade6;
            }''')
        
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        
        # Add color selection submenu
        color_menu = QtWidgets.QMenu("Color")
        color_menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        color_menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        color_menu.setStyleSheet(menu.styleSheet())
        menu.addMenu(color_menu)
        
        color_widget = QtWidgets.QWidget()
        color_layout = QtWidgets.QGridLayout(color_widget)
        color_layout.setSpacing(5)
        color_layout.setContentsMargins(3,5,3,5)
        
        for i, color in enumerate(self.color_palette):
            color_button = ColorButton(color)
            color_button.clicked.connect(self.create_color_change_function(button, color))
            color_layout.addWidget(color_button, i // 4, i % 4)
        
        color_action = QtWidgets.QWidgetAction(color_menu)
        color_action.setDefaultWidget(color_widget)
        color_menu.addAction(color_action)
        
        # Add "Move to" submenu
        move_menu = QtWidgets.QMenu("Move to")
        move_menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        move_menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        move_menu.setStyleSheet(menu.styleSheet())
        menu.addMenu(move_menu)
        
        for tab_name in self.tabs.keys():
            if tab_name != self.current_tab:
                tab_action = move_menu.addAction(tab_name)
                tab_action.triggered.connect(self.create_move_to_tab_function(button, tab_name))
        
        action = menu.exec_(button.mapToGlobal(pos))
        self.context_menu_open = False
        if self.fade_away_enabled:
            self.fade_timer.start(10)
        if action == rename_action:
            self.rename_selection_button(button)
        elif action == delete_action:
            self.delete_selection_button(button)

    def create_color_change_function(self, button, color):
        def change_color():
            self.set_button_color(button, color)
            self.update_selection_color(button.text(), color)
        return change_color

    def create_move_to_tab_function(self, button, tab_name):
        def move_to_tab():
            self.move_button_to_tab(button, tab_name)
        return move_to_tab

    def set_button_color(self, button, color):
        button.setStyleSheet(f'''
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 3px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color)};
            }}
            QToolTip {{background-color: {color};color: white;border: 0px;}}
        ''')

    def update_selection_color(self, selection_name, color):
        selection_dict = self.get_selection_dict()
        if selection_name in selection_dict['selections']:
            selection_dict['selections'][selection_name]['color'] = color
            self.save_selection_dict(selection_dict)

    def lighten_color(self, color, factor=1.2):
        c = QColor(color)
        h, s, l, a = c.getHsl()
        l = min(int(l * factor), 255)
        c.setHsl(h, s, l, a)
        return c.name()

    def rename_selection_button(self, button):
        dialog = CustomDialog(self, "Rename Selection", (150, 110))
        dialog.add_widget(QtWidgets.QLabel("Enter new name:"))
        input_field = QtWidgets.QLineEdit(button.text())
        dialog.add_widget(input_field)
        dialog.add_button_box()

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_name = input_field.text()
            if new_name and new_name != button.text():
                old_name = button.text()
                selection_dict = self.get_selection_dict()

                # Check if the new name already exists in any tab
                while any(new_name in tab_selections for tab_selections in selection_dict['tabs'].values()):
                    new_name += "_1"

                if old_name in selection_dict['selections']:
                    selection_dict['selections'][new_name] = selection_dict['selections'].pop(old_name)
                    for tab, selections in selection_dict['tabs'].items():
                        if old_name in selections:
                            selections[selections.index(old_name)] = new_name
                    self.save_selection_dict(selection_dict)

                button.setText(new_name)
                button.setFixedWidth(button.calculate_button_width(new_name))

                # Update the button's click connection
                button.clicked.disconnect()
                button.clicked.connect(lambda: self.select_objects(new_name, QtWidgets.QApplication.keyboardModifiers()))

    def delete_selection_button(self, button):
        dialog = CustomDialog(self, "Delete Confirmation", (160, 80))
        dialog.add_widget(QtWidgets.QLabel(f"Are you sure you want to <br> delete  <b>'{button.text()}'<b>? "))
        dialog.add_button_box()

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selection_name = button.text()
            selection_dict = self.get_selection_dict()
            if selection_name in selection_dict['selections']:
                del selection_dict['selections'][selection_name]
                for tab, selections in selection_dict['tabs'].items():
                    if selection_name in selections:
                        selections.remove(selection_name)
                self.save_selection_dict(selection_dict)
                # Remove the button from the current tab
                self.tabs[self.current_tab].remove(button)
                self.selectionButtonsLayout.removeWidget(button)
                button.deleteLater()

    def update_selection_buttons(self):
        if not hasattr(self, 'selectionButtonsLayout'):
            print("Error: selectionButtonsLayout not initialized")
            return

        # Clear existing buttons
        for i in reversed(range(self.selectionButtonsLayout.count())):
            widget = self.selectionButtonsLayout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Add new buttons for the current tab
        for button in self.tabs[self.current_tab]:
            self.selectionButtonsLayout.addWidget(button)
        maya_main_window().activateWindow()
    
    # Database operations
    def save_selection(self):
        dialog = CustomDialog(self, "Save Selection", (200, 160))
        dialog.add_widget(QtWidgets.QLabel("Enter selection name:"))
        input_field = QtWidgets.QLineEdit()
        dialog.add_widget(input_field)
        dialog.add_widget(QtWidgets.QLabel("Select tab:"))
        tab_combo = QtWidgets.QComboBox()
        tab_combo.addItems(self.tabs.keys())
        tab_combo.setCurrentText(self.current_tab)
        dialog.add_widget(tab_combo)
        dialog.add_button_box()

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selection_name = input_field.text()
            selected_tab = tab_combo.currentText()
            if selection_name:
                current_selection = cmds.ls(selection=True, long=True)
                if not current_selection:
                    cmds.warning("No objects selected.")
                    return

                selection_dict = self.get_selection_dict()

                # Ensure unique name across all tabs
                while any(selection_name in tab_selections for tab_selections in selection_dict['tabs'].values()):
                    selection_name += "_1"

                # Update the selections dictionary
                selection_dict['selections'][selection_name] = {
                    'objects': current_selection,
                    'color': self.color_palette[0]  # Default color
                }

                # Update the tabs dictionary
                if selected_tab not in selection_dict['tabs']:
                    selection_dict['tabs'][selected_tab] = []
                selection_dict['tabs'][selected_tab].append(selection_name)

                self.save_selection_dict(selection_dict)
                self.switch_tab(selected_tab)
                self.add_selection_button(selection_name)

                #cmds.inViewMessage(amg=f"Selection saved as '{selection_name}' in tab '{selected_tab}'", pos='midCenter', fade=True)

    def delete_selection(self, selection_name):
        selection_dict = self.get_selection_dict()
        if selection_name in selection_dict:
            del selection_dict[selection_name]
            self.save_selection_dict(selection_dict)
            for i in range(self.selectionButtonsLayout.count()):
                widget = self.selectionButtonsLayout.itemAt(i).widget()
                if widget and widget.text() == selection_name:
                    widget.deleteLater()
                    self.selectionButtonsLayout.removeWidget(widget)
                    break
            self.selectionButtonsLayout.update()
            self.update_database_order()  # Update order after deletion
        else:
            cmds.warning(f"Selection '{selection_name}' not found.")

    def rename_selection(self, old_name, new_name):
        selection_dict = self.get_selection_dict()
        if old_name in selection_dict:
            selection_dict[new_name] = selection_dict.pop(old_name)
            self.save_selection_dict(selection_dict)
            #self.update_database_order() 
        else:
            cmds.warning(f"Selection '{old_name}' not found.")

    def select_objects(self, selection_name, modifiers):
        selection_dict = self.get_selection_dict()
        
        # Check if the selection exists
        if selection_name in selection_dict['selections']:
            objects = selection_dict['selections'][selection_name]['objects']
            
            # Ensure objects is a list
            if isinstance(objects, list):
                # Check for Shift modifier to add to selection
                if modifiers == QtCore.Qt.ShiftModifier:
                    cmds.select(objects, add=True)
                else:
                    cmds.select(objects, replace=True)
            else:
                cmds.warning(f"Invalid data for selection '{selection_name}'.")
        else:
            cmds.warning(f"Selection '{selection_name}' not found.")
        
        maya_main_window().activateWindow()
    
    def get_selection_dict(self):
        if not cmds.objExists('defaultObjectSet'):
            cmds.createNode('objectSet', name='defaultObjectSet')
        if not cmds.attributeQuery('selectToolData', node='defaultObjectSet', exists=True):
            cmds.addAttr('defaultObjectSet', longName='selectToolData', dataType='string')
            return {'selections': {}, 'tabs': {}}

        data = cmds.getAttr('defaultObjectSet.selectToolData')
        if data:
            try:
                ordered_dict = json.loads(data)
                result_dict = {'selections': {}, 'tabs': {}}

                # Process selections
                if 'selections' in ordered_dict:
                    for key, value in ordered_dict['selections'].items():
                        if isinstance(value, dict) and 'objects' in value:
                            result_dict['selections'][key] = value
                        else:
                            result_dict['selections'][key] = {'objects': value, 'color': None}

                # Process tabs
                if 'tabs' in ordered_dict:
                    result_dict['tabs'] = ordered_dict['tabs']

                return result_dict
            except json.JSONDecodeError:
                cmds.warning("Invalid data in selectToolData. Resetting.")
                return {'selections': {}, 'tabs': {}}

        return {'selections': {}, 'tabs': {}}

    def save_selection_dict(self, selection_dict):
        ordered_dict = {
            'selections': {
                key: {
                    'order': i,
                    'objects': value['objects'],
                    'color': value.get('color')
                }
                for i, (key, value) in enumerate(selection_dict['selections'].items())
            },
            'tabs': selection_dict['tabs']
        }
        cmds.setAttr('defaultObjectSet.selectToolData', json.dumps(ordered_dict), type='string')

    def update_database_order(self):
        selection_dict = self.get_selection_dict()
        new_order = {'selections': {}, 'tabs': selection_dict['tabs'].copy()}

        # Update the order of selections in the current tab
        new_order['tabs'][self.current_tab] = []
        for button in self.tabs[self.current_tab]:
            selection_name = button.text()
            new_order['tabs'][self.current_tab].append(selection_name)
            if selection_name in selection_dict['selections']:
                new_order['selections'][selection_name] = selection_dict['selections'][selection_name]

        # Preserve other selections that are not in the current tab
        for selection, data in selection_dict['selections'].items():
            if selection not in new_order['selections']:
                new_order['selections'][selection] = data

        self.save_selection_dict(new_order)
    
    def populate_existing_selections(self):
        selection_dict = self.get_selection_dict()
        
        # Clear existing tabs and buttons
        self.tabs.clear()
        for i in reversed(range(self.selectionButtonsLayout.count())):
            widget = self.selectionButtonsLayout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # Iterate through each tab and add buttons
        for tab_name, selections in selection_dict['tabs'].items():
            if tab_name not in self.tabs:
                self.add_tab(tab_name)
            
            self.tabs[tab_name] = []
            for selection_name in selections:
                if selection_name in selection_dict['selections']:
                    button = self.create_selection_button(selection_name)
                    self.tabs[tab_name].append(button)

        # Switch to the first tab after populating
        if self.tabs:
            first_tab = next(iter(self.tabs))
            self.switch_tab(first_tab)

def show_select_set_tool():
    try:
        global select_set_tool_widget
        
        if hasattr(maya_main_window(), '_select_set_tool_widget'):
            maya_main_window()._select_set_tool_widget.close()
            maya_main_window()._select_set_tool_widget.deleteLater()
            
    except:
        pass
    
    select_set_tool_widget = SelectSetToolWindow(parent=maya_main_window())
    select_set_tool_widget.setObjectName("selectSetTool")
    select_set_tool_widget.move(400, 780)
    select_set_tool_widget.show()

    maya_main_window()._select_set_tool_widget = select_set_tool_widget
    maya_main_window().activateWindow()

show_select_set_tool()
