import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMayaUI as omui
from PySide2 import QtWidgets, QtCore, QtGui
from shiboken2 import wrapInstance

def create_save_selection_tool_button():
    button_command ="""
import maya.cmds as cmds
from maya import OpenMayaUI as omui
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

class DraggableButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super(DraggableButton, self).__init__(text, parent)
        self.setStyleSheet('''
            QPushButton {
                background-color: #4d4d4d;
                color: white;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
        ''')
        self.setFixedHeight(24)
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

class SelectSetToolWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SelectSetToolWindow, self).__init__(maya_main_window(), QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setWindowTitle("SelectSetTool")
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setStyleSheet('''QWidget {background-color: rgba(0, 0, 0, 0);}
                            QDialog, QMessageBox {background-color: #444444 ;color: #222222;}
                            QLabel {color: #ffffff;}
                            QLineEdit {background-color: #333333;color: #ffffff;border: 0px solid #555555; padding: 2px;}
                            QPushButton {background-color: #333333;color: white;border-radius: 3px;padding: 5px;}
                            QPushButton:hover {background-color: #5a5a5a;}''')

        self.setup_ui()
        self.setup_connections()
        self.populate_existing_selections()

        self.color_palette = [
            "#4d4d4d", "#d58c09", "#16aaa6", "#9416ca",
            "#873b75", "#6c9809", "#293f64", "#cf2222"
        ]
        
        # Set initial opacity
        self.setWindowOpacity(1)
        
        # Create timer and animation
        self.fade_timer = QTimer(self)
        self.fade_timer.setSingleShot(True)
        self.fade_timer.timeout.connect(self.start_fade_animation)
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(1000)  # 500 ms for fade effect
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Set up right-click menu for the frame
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_frame_context_menu)
        self.fade_away_enabled = False

    def setup_ui(self):
        # Main layout setup
        self.mainLayout = QtWidgets.QHBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        # Frame setup
        self.frame = QtWidgets.QFrame(self)
        self.frame.setStyleSheet('''
            QFrame {
                border: 0px solid gray;
                border-radius: 5px;
                background-color: rgba(40, 40, 40, .6);
            }
        ''')
        frameLayout = QtWidgets.QVBoxLayout(self.frame)

        # Button layout setup
        closeButtonLayout = QtWidgets.QHBoxLayout()
        self.setup_save_button(closeButtonLayout)
        self.setup_close_button(closeButtonLayout)
        frameLayout.addLayout(closeButtonLayout)

        # Selection buttons layout
        self.selectionButtonsLayout = QtWidgets.QHBoxLayout()
        self.selectionButtonsLayout.setSpacing(5)
        self.selectionButtonsLayout.setAlignment(QtCore.Qt.AlignLeft)
        frameLayout.addLayout(self.selectionButtonsLayout)

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
        layout.addWidget(self.saveSelectionButton)
        layout.addStretch()

    def setup_close_button(self, layout):
        self.closeButton = QtWidgets.QPushButton("✕", self)
        self.closeButton.setStyleSheet('''
            QPushButton {background-color: rgba(200, 0, 0, 0.6);color: white;border: none;border-radius: 3px;padding: 2px;}
            QPushButton:hover {background-color: rgba(255, 0, 0, 0.6);}''')
        
        self.closeButton.setToolTip('Close tool')
        self.closeButton.setFixedSize(18, 18)
        layout.addWidget(self.closeButton)

    def setup_connections(self):
        self.saveSelectionButton.clicked.connect(self.save_selection)
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
            self.update_database_order()

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
        if self.fade_away_enabled:
            self.fade_timer.start(1000)  # 1000ms delay before fade out
        super(SelectSetToolWindow, self).leaveEvent(event)

    def start_fade_animation(self):
        if self.fade_away_enabled:
            self.fade_animation.setDuration(1000)  # 1000ms for fade out
            self.fade_animation.setStartValue(self.windowOpacity())
            self.fade_animation.setEndValue(0.2)
            self.fade_animation.start()

    # Core Functionality        
    def calculate_button_width(self, text, padding=20):
        font_metrics = QtGui.QFontMetrics(self.font())
        text_width = font_metrics.horizontalAdvance(text)
        return text_width + padding
    
    def add_selection_button(self, selection_name):
        button = DraggableButton(selection_name)
        button.clicked.connect(lambda: self.select_objects(selection_name, QtWidgets.QApplication.keyboardModifiers()))
        button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(lambda pos, btn=button: self.show_context_menu(pos, btn))
        
        # Set color if it exists in the database
        selection_dict = self.get_selection_dict()
        if selection_name in selection_dict and 'color' in selection_dict[selection_name]:
            color = selection_dict[selection_name]['color']
            if color:
                self.set_button_color(button, color)
        
        self.selectionButtonsLayout.addWidget(button)

    def show_frame_context_menu(self, pos):
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
        if action == toggle_fade_action:
            self.toggle_fade_away()

    def toggle_fade_away(self):
        self.fade_away_enabled = not self.fade_away_enabled
        if not self.fade_away_enabled:
            self.fade_timer.stop()
            self.fade_animation.stop()
            self.setWindowOpacity(1.0)

    def show_context_menu(self, pos, button):
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
            color_button.clicked.connect(lambda c=color, b=button: self.set_button_color(b, c))
            color_layout.addWidget(color_button, i // 4, i % 4)
        
        color_action = QtWidgets.QWidgetAction(color_menu)
        color_action.setDefaultWidget(color_widget)
        color_menu.addAction(color_action)
        
        action = menu.exec_(button.mapToGlobal(pos))
        if action == rename_action:
            self.rename_selection_button(button)
        elif action == delete_action:
            self.delete_selection_button(button)

    def set_button_color(self, button, color):
        button.setStyleSheet(f'''
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 3px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color)};
            }}
        ''')
        self.update_selection_color(button.text(), color)

    def lighten_color(self, color, factor=1.2):
        c = QColor(color)
        h, s, l, a = c.getHsl()
        l = min(int(l * factor), 255)
        c.setHsl(h, s, l, a)
        return c.name()
    
    def update_selection_color(self, selection_name, color):
        selection_dict = self.get_selection_dict()
        if selection_name in selection_dict:
            if isinstance(selection_dict[selection_name], dict):
                selection_dict[selection_name]['color'] = color
            else:
                selection_dict[selection_name] = {
                    'objects': selection_dict[selection_name],
                    'color': color
                }
            self.save_selection_dict(selection_dict)

    def rename_selection_button(self, button):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Rename Selection")
        dialog.setFixedSize(200, 100)

        layout = QtWidgets.QVBoxLayout(dialog)
        
        input_field = QtWidgets.QLineEdit(button.text())
        layout.addWidget(QtWidgets.QLabel("Enter new name:"))
        layout.addWidget(input_field)
        
        button_layout = QtWidgets.QHBoxLayout()
        apply_button = QtWidgets.QPushButton("Apply")
        close_button = QtWidgets.QPushButton("Close")

        button_layout.addWidget(apply_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        apply_button.clicked.connect(dialog.accept)
        close_button.clicked.connect(dialog.reject)
        
        input_field.returnPressed.connect(dialog.accept)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_name = input_field.text()
            if new_name and new_name != button.text():
                old_name = button.text()
            
                # Disconnect the old connection
                button.clicked.disconnect()
                
                self.rename_selection(old_name, new_name)
                button.setText(new_name)
                
                # Reconnect with the new name
                button.clicked.connect(lambda: self.select_objects(new_name))
                
                # Recalculate and set the new width of the button
                new_width = button.calculate_button_width(new_name)
                button.setFixedWidth(new_width)

    def delete_selection_button(self, button):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Delete Confirmation")
        dialog.setFixedSize(200, 100)

        layout = QtWidgets.QVBoxLayout(dialog)
        
        layout.addWidget(QtWidgets.QLabel("Are you sure you want to delete"))
        layout.addWidget(QtWidgets.QLabel(f"<div align='center'><b>{button.text()}?</b></div>"))
        
        button_layout = QtWidgets.QHBoxLayout()
        apply_button = QtWidgets.QPushButton("Apply")
        close_button = QtWidgets.QPushButton("Close")

        button_layout.addWidget(apply_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        apply_button.clicked.connect(dialog.accept)
        close_button.clicked.connect(dialog.reject)
        
        dialog.setFocus()  # Set focus to the dialog so it can receive key events
        dialog.keyPressEvent = lambda e: dialog.accept() if e.key() == QtCore.Qt.Key_Return else super(QtWidgets.QDialog, dialog).keyPressEvent(e)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.delete_selection(button.text())
            self.selectionButtonsLayout.removeWidget(button)
            button.deleteLater()

    # Database operations
    def save_selection(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Save Selection")
        dialog.setFixedSize(200, 100)

        layout = QtWidgets.QVBoxLayout(dialog)
        
        input_field = QtWidgets.QLineEdit()
        layout.addWidget(QtWidgets.QLabel("Enter selection name:"))
        layout.addWidget(input_field)
        
        button_layout = QtWidgets.QHBoxLayout()
        apply_button = QtWidgets.QPushButton("Apply")
        close_button = QtWidgets.QPushButton("Close")
        
        button_layout.addWidget(apply_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        apply_button.clicked.connect(dialog.accept)
        close_button.clicked.connect(dialog.reject)
        
        input_field.returnPressed.connect(dialog.accept)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selection_name = input_field.text()
            if selection_name:
                current_selection = cmds.ls(selection=True, long=True)
                if not current_selection:
                    cmds.warning("No objects selected.")
                    return
                
                selection_dict = self.get_selection_dict()
                
                # Ensure unique name
                base_name = selection_name
                counter = 1
                while selection_name in selection_dict:
                    selection_name = f"{base_name}_{counter}"
                    counter += 1
                
                selection_dict[selection_name] = current_selection
                self.save_selection_dict(selection_dict)
                self.add_selection_button(selection_name)

    def select_objects(self, selection_name, modifiers):
        selection_dict = self.get_selection_dict()
        if selection_name in selection_dict:
            objects = selection_dict[selection_name]['objects']
            if isinstance(objects, list):
                if modifiers == QtCore.Qt.ShiftModifier:
                    # Add to current selection
                    cmds.select(objects, add=True)
                else:
                    # Replace current selection
                    cmds.select(objects, replace=True)
            else:
                cmds.warning(f"Invalid data for selection '{selection_name}'.")
        else:
            cmds.warning(f"Selection '{selection_name}' not found.")
        maya_main_window().activateWindow()
    
    def rename_selection(self, old_name, new_name):
        selection_dict = self.get_selection_dict()
        if old_name in selection_dict:
            selection_dict[new_name] = selection_dict.pop(old_name)
            self.save_selection_dict(selection_dict)
            #self.update_database_order() 
        else:
            cmds.warning(f"Selection '{old_name}' not found.")

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

    def get_selection_dict(self):
        if not cmds.objExists('defaultObjectSet'):
            cmds.createNode('objectSet', name='defaultObjectSet')
        if not cmds.attributeQuery('selectToolData', node='defaultObjectSet', exists=True):
            cmds.addAttr('defaultObjectSet', longName='selectToolData', dataType='string')
            return {}
        data = cmds.getAttr('defaultObjectSet.selectToolData')
        if data:
            try:
                ordered_dict = json.loads(data)
                # Flatten nested dictionaries
                flattened_dict = {}
                for key, value in ordered_dict.items():
                    if isinstance(value, dict):
                        if 'objects' in value:
                            flattened_dict[key] = value
                        else:
                            flattened_dict[key] = {'objects': value, 'color': None}
                    else:
                        flattened_dict[key] = {'objects': value, 'color': None}
                return flattened_dict
            except json.JSONDecodeError:
                cmds.warning("Invalid data in selectToolData. Resetting.")
                return {}
        return {}

    def save_selection_dict(self, selection_dict):
        ordered_dict = {key: {'order': i, 'objects': value['objects'], 'color': value.get('color')} 
                        for i, (key, value) in enumerate(selection_dict.items())}
        cmds.setAttr('defaultObjectSet.selectToolData', json.dumps(ordered_dict), type='string')

    def update_database_order(self):
        selection_dict = self.get_selection_dict()
        new_order = {}
        for i in range(self.selectionButtonsLayout.count()):
            widget = self.selectionButtonsLayout.itemAt(i).widget()
            if isinstance(widget, DraggableButton):
                new_order[widget.text()] = selection_dict[widget.text()]
        self.save_selection_dict(new_order)
    
    def populate_existing_selections(self):
        selection_dict = self.get_selection_dict()
        for selection_name in selection_dict.keys():
            self.add_selection_button(selection_name)

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
    select_set_tool_widget.move(400, 800)
    select_set_tool_widget.show()

    maya_main_window()._select_set_tool_widget = select_set_tool_widget
    maya_main_window().activateWindow()

show_select_set_tool()
"""
    gShelfTopLevel = mel.eval("$tmpVar=$gShelfTopLevel")
    if gShelfTopLevel:
        current_shelf = cmds.tabLayout(gShelfTopLevel, query=True, selectTab=True)
        shelf_button = cmds.shelfButton(
            parent=current_shelf,
            command=button_command,
            annotation="Open Save Selection Tool",
            label="Save Selection Tool",
            image="pythonFamily.png",
            imageOverlayLabel="SST",
            overlayLabelColor=[1, 1, 1],
            overlayLabelBackColor=[0, 0, 0, 0],
            backgroundColor=[0.049, 0.398, 0.504],
            sourceType="python"
        )
        print("Button created:", shelf_button)
    else:
        cmds.warning("No active shelf found.")

def onMayaDroppedPythonFile(*args, **kwargs):
    create_save_selection_tool_button()

if __name__ == "__main__":
    onMayaDroppedPythonFile()
