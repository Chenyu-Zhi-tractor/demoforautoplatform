import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView, 
    QPushButton, QTabWidget, QComboBox, QStyledItemDelegate, QAbstractItemView, QStyle
)
from PyQt6.QtGui import QColor, QBrush, QStandardItemModel, QStandardItem, QTextDocument
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSize

class WrappingItemDelegate(QStyledItemDelegate):
    """支持文本自动换行的委托"""
    def paint(self, painter, option, index):
        # 手动绘制背景色（从模型的 BackgroundRole 获取）
        bg = index.data(Qt.ItemDataRole.BackgroundRole)
        if bg:
            painter.fillRect(option.rect, bg)
        elif option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())
        
        # 绘制自动换行的文本
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text:
            doc = QTextDocument()
            doc.setDefaultFont(option.font)
            doc.setPlainText(text)
            doc.setTextWidth(option.rect.width() - 8)  # 留一些边距
            
            painter.save()
            painter.translate(option.rect.left() + 4, option.rect.top() + 4)
            doc.drawContents(painter)
            painter.restore()
    
    def sizeHint(self, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text:
            doc = QTextDocument()
            doc.setDefaultFont(option.font)
            doc.setPlainText(text)
            doc.setTextWidth(option.rect.width() - 8)
            return doc.size().toSize() + QSize(8, 8)  # 加上边距
        return super().sizeHint(option, index)
# === Global Helper ===
def get_port_usage(pump_id, all_data_context):
    """
    Returns a dict {port_num: usage_description_string}
    all_data_context must provide access to connections, liquids, etc.
    """
    usage = {}
    if not pump_id: return usage
    
    pid = int(pump_id)
    
    # Check Connections
    for conn in all_data_context.get('connections', []):
        if conn.get('pump_a') == pid:
            usage[conn.get('port_a')] = f"Pump{conn.get('pump_b')}"
        if conn.get('pump_b') == pid:
            usage[conn.get('port_b')] = f"Pump{conn.get('pump_a')}"

    # Check Resources
    for cat in ['liquids', 'gases', 'containers']:
        for item in all_data_context.get(cat, []):
            if item.get('pump') == pid:
                usage[item.get('port')] = f"{cat[:-1].title()}:{item.get('name', '')}"
                
    return usage

# === Delegates ===

class PumpDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings or {}

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        count = int(self.settings.get('pump_count', 4))
        for i in range(1, count + 1):
            editor.addItem(str(i))
        return editor

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.ItemDataRole.EditRole)
        if val:
            editor.setCurrentText(str(val))

    def setModelData(self, editor, model, index):
        try:
            val = int(editor.currentText())
            model.setData(index, val, Qt.ItemDataRole.EditRole)
        except:
            pass

class PortDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, settings=None, data_context=None, pump_col_idx=None):
        super().__init__(parent)
        self.settings = settings or {}
        self.data_context = data_context or {}
        self.pump_col_idx = pump_col_idx # The column index where Pump ID is stored corresponding to this port

    def createEditor(self, parent, option, index):
        # 1. Find the Pump ID for this row
        model = index.model()
        # The pump column is in the same row
        pump_idx = model.index(index.row(), self.pump_col_idx)
        pump_val = model.data(pump_idx, Qt.ItemDataRole.EditRole)
        
        editor = QComboBox(parent)
        item_model = QStandardItemModel()
        
        port_count = int(self.settings.get('port_count', 8))
        
        # Get usage for this pump
        usage_map = get_port_usage(pump_val, self.data_context) if pump_val else {}
        
        # Current value (we shouldn't mark OURSELVES as conflict if we are just editing)
        # But for simplicity, we just show what's occuping.
        
        for i in range(1, port_count + 1):
            item = QStandardItem(str(i))
            usage = usage_map.get(i)
            
            if usage:
                item.setText(f"{i} ({usage})")
                # Removed red highlight as per request
            
            item_model.appendRow(item)
            
        editor.setModel(item_model)
        return editor

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.ItemDataRole.EditRole)
        # We need to match the number part, because text might be "1 (Liquid:A)"
        if val:
            # Find the item that starts with the number
            s_val = str(val)
            for i in range(editor.count()):
                text = editor.itemText(i)
                # Check if text is "X" or "X (Usage)"
                if text == s_val or text.startswith(s_val + " "):
                    editor.setCurrentIndex(i)
                    break

    def setModelData(self, editor, model, index):
        text = editor.currentText()
        # Extract number "1 (Liquid...)" -> "1"
        num_str = text.split(' ')[0]
        try:
            if not num_str: return
            val = int(num_str)
            model.setData(index, val, Qt.ItemDataRole.EditRole)
        except:
            pass

# === Models ===

# (Reusing previous model logic but ensuring setData handles ints correctly)

class ConnectionTableModel(QAbstractTableModel):
    def __init__(self, connections=None):
        super().__init__()
        # If connections is an empty list, 'or []' creates a NEW list!
        # We must use the reference passed in if it's not None.
        if connections is None:
            self.connections = []
        else:
            self.connections = connections
            
        self.headers = ["Pump A", "Port A", "Pump B", "Port B"]

    def rowCount(self, parent=QModelIndex()): return len(self.connections)
    def columnCount(self, parent=QModelIndex()): return 4
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        row, col = index.row(), index.column()
        if row >= len(self.connections): return None
        conn = self.connections[row]
        
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            keys = ['pump_a', 'port_a', 'pump_b', 'port_b']
            return str(conn.get(keys[col], ''))
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole: return False
        try: val = int(value)
        except: return False
            
        keys = ['pump_a', 'port_a', 'pump_b', 'port_b']
        self.connections[index.row()][keys[index.column()]] = val
        self.dataChanged.emit(index, index, [role])
        return True

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None
    
    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def add_row(self):
        self.beginInsertRows(QModelIndex(), len(self.connections), len(self.connections))
        # Default to safe values
        self.connections.append({'pump_a': 1, 'port_a': 1, 'pump_b': 1, 'port_b': 1})
        self.endInsertRows()

    def remove_row(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        self.connections.pop(row)
        self.endRemoveRows()

    def reload(self):
        self.beginResetModel()
        self.endResetModel()

class ResourceTableModel(QAbstractTableModel):
    def __init__(self, data_list=None, headers=None):
        super().__init__()
        # Fix: Ensure we use the reference if provided
        if data_list is None:
            self.data_list = []
        else:
            self.data_list = data_list
            
        self.headers = headers or ["ID", "Name/Desc", "Pump", "Port"]

    def rowCount(self, parent=QModelIndex()): return len(self.data_list)
    def columnCount(self, parent=QModelIndex()): return 4

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        row, col = index.row(), index.column()
        if row >= len(self.data_list): return None
        item = self.data_list[row]
        
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == 0: return item.get('id', '')
            if col == 1: return item.get('name', '')
            if col == 2: return str(item.get('pump', ''))
            if col == 3: return str(item.get('port', ''))
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole: return False
        
        row, col = index.row(), index.column()
        # Improve safety: extend list if index out of bounds (shouldn't happen)
        if row >= len(self.data_list): return False
        
        item = self.data_list[row]
        
        # ID Column (0) is auto-managed, do not edit
        if col == 0: 
            return False
            
        elif col == 1: 
            item['name'] = str(value)
        elif col in (2, 3):
            try: 
                # Handle empty strings or None which might come from clears
                if value is None or value == "":
                    pass # Don't update
                else:
                    val = int(value)
                    item['pump' if col == 2 else 'port'] = val
            except: 
                pass
            
        self.dataChanged.emit(index, index, [role])
        return True

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def flags(self, index):
        # ID Column (0) is read-only
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() != 0:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def add_row(self):
        # Auto-assign ID based on current count
        next_id = str(len(self.data_list))
        self.beginInsertRows(QModelIndex(), len(self.data_list), len(self.data_list))
        self.data_list.append({'id': next_id, 'name': '', 'pump': 1, 'port': 1})
        self.endInsertRows()

    def remove_row(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        self.data_list.pop(row)
        self.endRemoveRows()
        self._renumber()

    def _renumber(self):
        """Renumber all items to 0, 1, 2..."""
        for i, item in enumerate(self.data_list):
            item['id'] = str(i)
        
        # Update view for ID column
        if self.data_list:
            topLeft = self.index(0, 0)
            bottomRight = self.index(len(self.data_list)-1, 0)
            self.dataChanged.emit(topLeft, bottomRight, [Qt.ItemDataRole.DisplayRole])

    def reload(self):
        # Force renumbering on load/reload to ensure consistency
        for i, item in enumerate(self.data_list):
            item['id'] = str(i)
        self.beginResetModel()
        self.endResetModel()

class UsageMatrixModel(QAbstractTableModel):
    def __init__(self, settings, connections, liquids, gases, containers):
        super().__init__()
        self.settings = settings
        self.connections = connections
        self.liquids = liquids
        self.gases = gases
        self.containers = containers

    def rowCount(self, parent=QModelIndex()): return int(self.settings.get('pump_count', 4))
    def columnCount(self, parent=QModelIndex()): return int(self.settings.get('port_count', 8))

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        pump_num = index.row() + 1
        port_num = index.column() + 1
        
        # Simplified context building
        ctx = {
            'connections': self.connections, 
            'liquids': self.liquids, 
            'gases': self.gases, 
            'containers': self.containers
        }
        usage_map = get_port_usage(pump_num, ctx)
        usage = usage_map.get(port_num)
        
        # Check conflicts more thoroughly:
        # get_port_usage overwrites duplicates, let's count properly
        usage_list = []
        for conn in self.connections:
            if conn.get('pump_a') == pump_num and conn.get('port_a') == port_num:
                 usage_list.append(f"Pump{conn.get('pump_b')}")
            elif conn.get('pump_b') == pump_num and conn.get('port_b') == port_num:
                 usage_list.append(f"Pump{conn.get('pump_a')}")
        
        for idx, item in enumerate(self.liquids):
             if item.get('pump') == pump_num and item.get('port') == port_num:
                 usage_list.append(f"liquid{idx}:\n{item.get('name', '')}")
        for idx, item in enumerate(self.gases):
             if item.get('pump') == pump_num and item.get('port') == port_num:
                 usage_list.append(f"gas{idx}:\n{item.get('name', '')}")
        for idx, item in enumerate(self.containers):
             if item.get('pump') == pump_num and item.get('port') == port_num:
                 usage_list.append(f"container{idx}:\n{item.get('name', '')}")
                 
        if role == Qt.ItemDataRole.DisplayRole:
            return "; ".join(usage_list)
        if role == Qt.ItemDataRole.BackgroundRole:
            if len(usage_list) > 1: return QBrush(QColor("#e74c3c"))
            if len(usage_list) == 1: return QBrush(QColor("#2ecc71"))
        return None
    
    def refresh(self):
        self.layoutChanged.emit()

# === Main Widget ===

class JsonEditorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        self.settings = {"pump_count": 4, "port_count": 8}
        self.connections = []
        self.liquids = []
        self.gases = []
        self.containers = []
        
        # Context pointer - using a method to always get current lists
        self.get_data_context = lambda: {
            'connections': self.connections,
            'liquids': self.liquids,
            'gases': self.gases,
            'containers': self.containers
        }
        
        self.init_connection_tab()
        self.init_resource_tab("Liquids", self.liquids)
        self.init_resource_tab("Gases", self.gases)
        self.init_resource_tab("Containers", self.containers)
        self.init_matrix_tab()
        
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def init_connection_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.conn_model = ConnectionTableModel(self.connections)
        view = QTableView()
        view.setModel(self.conn_model)
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Set Delegates
        # Pump A (0), Pump B (2)
        pump_del = PumpDelegate(view, self.settings)
        view.setItemDelegateForColumn(0, pump_del)
        view.setItemDelegateForColumn(2, pump_del)
        
        # Port A (1) - depends on Pump A (0)
        port_del_a = PortDelegate(view, self.settings, self.get_data_context(), pump_col_idx=0)
        view.setItemDelegateForColumn(1, port_del_a)
        
        # Port B (3) - depends on Pump B (2)
        port_del_b = PortDelegate(view, self.settings, self.get_data_context(), pump_col_idx=2)
        view.setItemDelegateForColumn(3, port_del_b)
        
        layout.addWidget(view)
        
        # Add Button (Styled & Explicit)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 添加连接 (Add Connection)")
        add_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 6px;")
        add_btn.clicked.connect(self.conn_model.add_row)
        
        del_btn = QPushButton("🗑️ 删除选中 (Remove Selected)")
        del_btn.setStyleSheet("padding: 6px;")
        del_btn.clicked.connect(lambda: self.remove_selected(view, self.conn_model))
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)
        
        self.tabs.addTab(tab, "Pump Connections")
        self.conn_view = view

    def init_resource_tab(self, title, data_list):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        model = ResourceTableModel(data_list)
        view = QTableView()
        view.setModel(model)
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Delegates
        # Pump is col 2
        pump_del = PumpDelegate(view, self.settings)
        view.setItemDelegateForColumn(2, pump_del)
        
        # Port is col 3, depends on pump col 2
        port_del = PortDelegate(view, self.settings, self.get_data_context(), pump_col_idx=2)
        view.setItemDelegateForColumn(3, port_del)
        
        layout.addWidget(view)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton(f"➕ 添加 {title} (Add)")
        add_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 6px;")
        add_btn.clicked.connect(model.add_row)
        
        del_btn = QPushButton("🗑️ 删除选中 (Remove Selected)")
        del_btn.setStyleSheet("padding: 6px;")
        del_btn.clicked.connect(lambda: self.remove_selected(view, model))
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)
        
        setattr(self, f"{title.lower()}_model", model)
        self.tabs.addTab(tab, title)

    def init_matrix_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.matrix_model = UsageMatrixModel(
            self.settings, self.connections, self.liquids, self.gases, self.containers
        )
        self.matrix_view = QTableView()
        self.matrix_view.setModel(self.matrix_model)
        self.matrix_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # 行高自适应文本内容
        self.matrix_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # 使用支持文本换行的委托
        wrapping_delegate = WrappingItemDelegate(self.matrix_view)
        self.matrix_view.setItemDelegate(wrapping_delegate)
        layout.addWidget(self.matrix_view)
        self.tabs.addTab(tab, "Port Usage Matrix")

    def remove_selected(self, view, model):
        selection = view.selectionModel().selectedRows()
        if not selection: return
        for index in sorted(selection, key=lambda x: x.row(), reverse=True):
            model.remove_row(index.row())

    def on_tab_changed(self, index):
        if index == self.tabs.count() - 1:
            self.matrix_model.refresh()

    def load_json(self, json_data):
        # Update settings dict IN PLACE so that delegates holding reference still see updates
        new_settings = json_data.get("settings", {})
        self.settings.update(new_settings)
        # Handle case where settings key is missing or partial
        if "pump_count" not in self.settings: self.settings["pump_count"] = 4
        if "port_count" not in self.settings: self.settings["port_count"] = 8
        
        self.connections[:] = json_data.get("connections", [])
        self.liquids[:] = json_data.get("liquids", [])
        self.gases[:] = json_data.get("gases", [])
        self.containers[:] = json_data.get("containers", [])
        
        self.conn_model.reload()
        self.liquids_model.reload()
        self.gases_model.reload()
        self.containers_model.reload()
        
        self.matrix_model.refresh()


    def to_json(self):
        # Explicitly grabbing data from models ensures we save what is shown in UI
        # even if list references somehow got desynchronized
        return {
            "settings": self.settings,
            "connections": self.conn_model.connections,
            "liquids": self.liquids_model.data_list,
            "gases": self.gases_model.data_list,
            "containers": self.containers_model.data_list
        }
