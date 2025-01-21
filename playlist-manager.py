import os
import json
import re
import shutil
import random
from PyQt5 import QtWidgets, QtGui, QtCore
from mutagen.id3 import ID3, COMM, ID3NoHeaderError
from mutagen.easyid3 import EasyID3
from collections import defaultdict

# Constants for JSON database
SONGS_DATABASE = "songs.json"  # Main database with song metadata
PLAYLISTS_DATABASE = "playlists.json"  # Database for playlist orders
ID_PREFIX = "ID"

# New constant for order pattern
ORDER_PATTERN = re.compile(r'^(\d{3})\s+(.+)$')

def add_id_to_metadata(file_path, song_id):
    """
    Add song ID to MP3 file metadata.
    """
    try:
        # Load the ID3 tag or create one if it doesn't exist
        try:
            audio = ID3(file_path)
        except ID3NoHeaderError:
            audio = ID3()
        
        # Remove existing comments and add new one
        audio.delall("COMM")
        audio.add(COMM(encoding=3, lang="eng", desc=song_id, text=song_id))
        
        # Save the updated tags
        audio.save(file_path)
        print(f"Added ID {song_id} to metadata of {file_path}")
        return True
        
    except Exception as e:
        print(f"Error adding metadata to {file_path}: {str(e)}")
        return False


def get_id_from_metadata(file_path):
    """
    Retrieve song ID from MP3 file metadata.
    """
    try:
        audio = ID3(file_path)
        for key in audio.keys():
            if key.startswith("COMM"):
                comment = audio[key].text[0]
                if comment.startswith("ID"):  # Check if it's our ID format
                    return comment
    except Exception as e:
        print(f"Error reading metadata from {file_path}: {str(e)}")
    return None

class EditDialog(QtWidgets.QDialog):
    def __init__(self, songs, parent=None):
        super().__init__(parent)
        self.songs = songs
        self.hide_numbers = False
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Edit Song Details")
        layout = QtWidgets.QVBoxLayout(self)

        if len(self.songs) == 1:  # Single song mode
            # Filename group
            filename_group = QtWidgets.QGroupBox("File Name")
            filename_layout = QtWidgets.QVBoxLayout()
            
            # File name edit with preview label
            self.filename_preview = QtWidgets.QLabel()
            filename_layout.addWidget(self.filename_preview)
            
            self.filename_edit = QtWidgets.QLineEdit(os.path.basename(self.songs[0]["path"]))
            self.filename_edit.textChanged.connect(self.update_preview)
            filename_layout.addWidget(self.filename_edit)
            
            filename_group.setLayout(filename_layout)
            layout.addWidget(filename_group)
            
            # Initial preview update
            self.update_preview()

        # Series editing
        series_group = QtWidgets.QGroupBox("Series")
        series_layout = QtWidgets.QVBoxLayout()
        self.series_edit = QtWidgets.QLineEdit(self.songs[0]["series"])
        series_layout.addWidget(self.series_edit)
        
        # Add OK button for series
        if len(self.songs) > 1:
            series_button = QtWidgets.QPushButton("OK")
            series_button.clicked.connect(lambda: self.apply_single_edit("series"))
            series_layout.addWidget(series_button)
        
        series_group.setLayout(series_layout)
        layout.addWidget(series_group)

        # Weight editing
        weight_group = QtWidgets.QGroupBox("Weight")
        weight_layout = QtWidgets.QVBoxLayout()
        self.weight_spin = QtWidgets.QSpinBox()
        self.weight_spin.setRange(1, 4)  # Modified range to 1-4
        self.weight_spin.setValue(self.songs[0]["weight"])
        weight_layout.addWidget(self.weight_spin)
        
        # Add OK button for weight
        if len(self.songs) > 1:
            weight_button = QtWidgets.QPushButton("OK")
            weight_button.clicked.connect(lambda: self.apply_single_edit("weight"))
            weight_layout.addWidget(weight_button)
        
        weight_group.setLayout(weight_layout)
        layout.addWidget(weight_group)

        # Buttons - only show for single song edit
        if len(self.songs) == 1:
            button_box = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
            )
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)
            layout.addWidget(button_box)

        if len(self.songs) > 1:
            msg = QtWidgets.QLabel(f"Editing {len(self.songs)} songs")
            msg.setStyleSheet("color: gray; font-style: italic;")
            layout.insertWidget(0, msg)
            
            # Add Cancel button at the bottom
            cancel_button = QtWidgets.QPushButton("Cancel")
            cancel_button.clicked.connect(self.reject)
            layout.addWidget(cancel_button)

    def apply_single_edit(self, field):
        """Apply edit for a single field (series or weight) across multiple songs"""
        all_songs = load_songs_from_database()
        
        try:
            for song in self.songs:
                db_song = next(s for s in all_songs if s["id"] == song["id"])
                if field == "series":
                    db_song["series"] = self.series_edit.text()
                elif field == "weight":
                    db_song["weight"] = self.weight_spin.value()
            
            save_songs_to_database(all_songs)
            self.parentWidget().refresh_all_views()
            self.parentWidget().statusBar().showMessage(f"{field.capitalize()} updated successfully")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error",
                f"An error occurred while updating {field}: {str(e)}"
            )

    def get_values(self):
        result = {
            "series": self.series_edit.text(),
            "weight": self.weight_spin.value()
        }
        if len(self.songs) == 1:
            result["filename"] = self.filename_edit.text()
        return result
    
    def toggle_number_display(self):
        self.hide_numbers = self.toggle_button.isChecked()
        self.update_preview()

    def update_preview(self):
        if len(self.songs) == 1:
            current_name = self.filename_edit.text()
            self.filename_preview.setText(f"Preview: {current_name}")

class OrderDialog(QtWidgets.QDialog):
    def __init__(self, max_order, parent=None):
        super().__init__(parent)
        self.max_order = max_order
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Set Order")
        layout = QtWidgets.QVBoxLayout(self)

        # Order input
        order_layout = QtWidgets.QHBoxLayout()
        self.order_spin = QtWidgets.QSpinBox()
        self.order_spin.setRange(1, self.max_order)
        order_layout.addWidget(QtWidgets.QLabel("New Order Position:"))
        order_layout.addWidget(self.order_spin)
        layout.addLayout(order_layout)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_order(self):
        return self.order_spin.value()

class OrderPreviewDialog(QtWidgets.QDialog):
    def __init__(self, current_order, max_order, parent=None):
        super().__init__(parent)
        self.current_order = current_order
        self.max_order = max_order
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Order Preview")
        self.setMinimumWidth(800)
        layout = QtWidgets.QVBoxLayout(self)

        # Explanation label
        explain_label = QtWidgets.QLabel(
            "Preview the new order below. You can drag and drop rows to adjust the order."
        )
        layout.addWidget(explain_label)

        # Preview table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Order", "ID", "Name", "Path", "Series", "Weight"])
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDropIndicatorShown(True)
        self.table.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        # Populate table
        self.populate_table()

        # Action buttons layout
        button_layout = QtWidgets.QHBoxLayout()

        # Apply method group
        method_group = QtWidgets.QGroupBox("Apply Method")
        method_layout = QtWidgets.QVBoxLayout()
        
        self.current_dir_radio = QtWidgets.QRadioButton("Modify Current Directory")
        self.current_dir_radio.setChecked(True)
        self.new_dir_radio = QtWidgets.QRadioButton("Copy to New Directory")
        
        method_layout.addWidget(self.current_dir_radio)
        method_layout.addWidget(self.new_dir_radio)
        method_group.setLayout(method_layout)
        button_layout.addWidget(method_group)

        # Action buttons
        button_box = QtWidgets.QDialogButtonBox()
        self.apply_button = button_box.addButton("Apply", QtWidgets.QDialogButtonBox.ActionRole)
        self.cancel_button = button_box.addButton(QtWidgets.QDialogButtonBox.Cancel)
        
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(button_box)
        layout.addLayout(button_layout)

    def populate_table(self):
        self.table.setRowCount(len(self.current_order))
        for i, row_data in enumerate(self.current_order):
            for j, text in enumerate(row_data):
                item = QtWidgets.QTableWidgetItem(str(text))
                self.table.setItem(i, j, item)

    def get_apply_method(self):
        return "current" if self.current_dir_radio.isChecked() else "new"

class PlaylistManagerUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Playlist Manager")
        self.setGeometry(100, 100, 1000, 700)
        self.current_folder = None
        self.hide_numbers = False
        
        # Create main widget and layout
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        
        # Create folder selection at the top
        folder_layout = QtWidgets.QHBoxLayout()
        self.folder_label = QtWidgets.QLabel("Current Folder:")
        self.folder_path = QtWidgets.QLineEdit()
        self.folder_path.setReadOnly(True)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_folder)
        # Add refresh button
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all_views)
        # Add delete playlist button
        self.delete_button = QtWidgets.QPushButton("Delete Playlist")
        self.delete_button.clicked.connect(self.delete_playlist)
        self.delete_button.setStyleSheet("QPushButton { color: red; }")
        
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_path)
        folder_layout.addWidget(self.browse_button)
        folder_layout.addWidget(self.refresh_button)
        folder_layout.addWidget(self.delete_button)
        main_layout.addLayout(folder_layout)
        
        # Tabs
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self.tab_registered = QtWidgets.QWidget()
        self.tab_unregistered = QtWidgets.QWidget()
        self.tab_order = OrderTab(self)
        self.tab_disabled = DisabledTab(self)  # Add new disabled tab
        
        self.tabs.addTab(self.tab_registered, "Registered Songs")
        self.tabs.addTab(self.tab_unregistered, "Unregistered Songs")
        self.tabs.addTab(self.tab_order, "Order Management")
        self.tabs.addTab(self.tab_disabled, "Disabled Songs")  # Add new tab
        
        # Setup tabs
        self.setup_registered_tab()
        self.setup_unregistered_tab()
        
        # Status bar
        self.statusBar().showMessage("Ready")

    def setup_registered_tab(self):
        layout = QtWidgets.QVBoxLayout()
        
        # Add filter controls
        filter_layout = QtWidgets.QHBoxLayout()
        self.filter_input = QtWidgets.QLineEdit()
        self.filter_input.setPlaceholderText("Search songs...")
        self.filter_input.textChanged.connect(self.filter_registered_songs)
        filter_layout.addWidget(self.filter_input)
        
        layout.addLayout(filter_layout)
        
        # Create custom item delegate for the Name column
        class NameDelegate(QtWidgets.QStyledItemDelegate):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.parent_window = parent

            def displayText(self, value, locale):
                if self.parent_window.hide_numbers:
                    match = ORDER_PATTERN.match(value)
                    if match:
                        return match.group(2)
                return value

        # Setup table with modified column behavior
        self.table_registered = QtWidgets.QTableWidget()
        self.table_registered.setColumnCount(6)
        self.table_registered.setHorizontalHeaderLabels(["Order", "ID", "Name", "Path", "Series", "Weight"])
        
        # Set individual column resize modes and default widths
        self.table_registered.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        self.table_registered.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        self.table_registered.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Interactive)
        self.table_registered.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Interactive)
        self.table_registered.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.Interactive)
        self.table_registered.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.Interactive)
        
        # Set default column widths
        self.table_registered.setColumnWidth(0, 60)   # Order
        self.table_registered.setColumnWidth(1, 80)   # ID
        self.table_registered.setColumnWidth(2, 300)  # Name
        self.table_registered.setColumnWidth(3, 300)  # Path
        self.table_registered.setColumnWidth(4, 150)  # Series
        self.table_registered.setColumnWidth(5, 60)   # Weight
        
        self.table_registered.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_registered.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table_registered.setSortingEnabled(True)
        
        # Connect sorting signal
        self.table_registered.horizontalHeader().sortIndicatorChanged.connect(self.on_sort_changed)
        layout.addWidget(self.table_registered)
        
        # [Rest of the setup_registered_tab remains the same]
        button_layout = QtWidgets.QHBoxLayout()
        self.edit_button = QtWidgets.QPushButton("Edit Selected")
        self.edit_button.clicked.connect(self.edit_selected_songs)
        self.remove_button = QtWidgets.QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected_songs)
        # self.reorder_button = QtWidgets.QPushButton("Change Order")
        # self.reorder_button.clicked.connect(self.change_order)
        # self.reorder_button.setEnabled(False)
        
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.remove_button)
        # button_layout.addWidget(self.reorder_button)
        layout.addLayout(button_layout)
        
        self.tab_registered.setLayout(layout)

        # Add toggle button for number display in main view
        self.main_toggle_button = QtWidgets.QPushButton("Toggle Number Display")
        self.main_toggle_button.setCheckable(True)
        self.main_toggle_button.clicked.connect(self.toggle_main_number_display)
        filter_layout.addWidget(self.main_toggle_button)

    def toggle_main_number_display(self):
        self.hide_numbers = self.main_toggle_button.isChecked()
        self.refresh_all_views()

    def extract_order_number(self, filename):
        """
        Instance method that uses the global function
        Kept for backward compatibility
        """
        return extract_order_number(filename)

    def setup_unregistered_tab(self):
        layout = QtWidgets.QVBoxLayout()
        
        # List widget with extended selection mode
        self.list_unregistered = QtWidgets.QListWidget()
        self.list_unregistered.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.list_unregistered)
        
        # Add buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.button_add = QtWidgets.QPushButton("Add Selected")
        self.button_add.clicked.connect(self.add_selected_songs)
        self.button_select_all = QtWidgets.QPushButton("Select All")
        self.button_select_all.clicked.connect(self.list_unregistered.selectAll)
        
        button_layout.addWidget(self.button_select_all)
        button_layout.addWidget(self.button_add)
        layout.addLayout(button_layout)
        
        self.tab_unregistered.setLayout(layout)

    def browse_folder(self):
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.current_folder = folder_path
            self.folder_path.setText(folder_path)
            self.refresh_all_views()
            self.statusBar().showMessage(f"Loaded folder: {folder_path}")

    def refresh_all_views(self):
        self.load_registered_songs()
        self.load_unregistered_songs()
        self.tab_order.refresh_view()
        self.tab_disabled.refresh_view()  # Add refresh for disabled tab

    def handle_sort(self, logical_index):
        if logical_index == 2:  # Name column
            self.table_registered.sortItems(2, QtCore.Qt.AscendingOrder if self.table_registered.horizontalHeader().sortIndicatorOrder() == QtCore.Qt.DescendingOrder else QtCore.Qt.DescendingOrder)
            self.refresh_all_views()

    def on_sort_changed(self, logical_index, order):
        """Handle sorting of columns"""
        self.load_registered_songs()

    def load_registered_songs(self):
        if not self.current_folder:
            return
            
        current_scroll = self.table_registered.verticalScrollBar().value()
        
        # Temporarily disable sorting to prevent recursion
        self.table_registered.setSortingEnabled(False)
        
        # Clear the table
        self.table_registered.setRowCount(0)
        
        # Load songs with their order information
        folder_songs = load_folder_songs(self.current_folder)
        
        # Get current sort column and order
        header = self.table_registered.horizontalHeader()
        sort_column = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        
        # Sort the songs list based on the current sort column
        if sort_column == 0:  # Order
            folder_songs.sort(key=lambda x: x.get("order", 0), reverse=(sort_order == QtCore.Qt.DescendingOrder))
        elif sort_column == 1:  # ID
            folder_songs.sort(key=lambda x: x["id"], reverse=(sort_order == QtCore.Qt.DescendingOrder))
        elif sort_column == 2:  # Name
            folder_songs.sort(key=lambda x: x["name"], reverse=(sort_order == QtCore.Qt.DescendingOrder))
        elif sort_column == 3:  # Path
            folder_songs.sort(key=lambda x: x["path"], reverse=(sort_order == QtCore.Qt.DescendingOrder))
        elif sort_column == 4:  # Series
            folder_songs.sort(key=lambda x: x["series"], reverse=(sort_order == QtCore.Qt.DescendingOrder))
        elif sort_column == 5:  # Weight
            folder_songs.sort(key=lambda x: x["weight"], reverse=(sort_order == QtCore.Qt.DescendingOrder))
        
        # Populate the table
        for row, song in enumerate(folder_songs):
            self.table_registered.insertRow(row)
            
            # Create and set items
            order_item = QtWidgets.QTableWidgetItem()
            order_item.setData(QtCore.Qt.DisplayRole, int(song.get("order", 0)))
            
            id_item = QtWidgets.QTableWidgetItem(song["id"])
            name_item = QtWidgets.QTableWidgetItem(song["name"])
            path_item = QtWidgets.QTableWidgetItem(song["path"])
            series_item = QtWidgets.QTableWidgetItem(song["series"])
            
            weight_item = QtWidgets.QTableWidgetItem()
            weight_item.setData(QtCore.Qt.DisplayRole, int(song["weight"]))
            
            # Set items
            self.table_registered.setItem(row, 0, order_item)
            self.table_registered.setItem(row, 1, id_item)
            self.table_registered.setItem(row, 2, name_item)
            self.table_registered.setItem(row, 3, path_item)
            self.table_registered.setItem(row, 4, series_item)
            self.table_registered.setItem(row, 5, weight_item)
        
        # Re-enable sorting
        self.table_registered.setSortingEnabled(True)
        
        # Restore scroll position
        self.table_registered.verticalScrollBar().setValue(current_scroll)

    def load_unregistered_songs(self):
        if not self.current_folder:
            return
            
        self.list_unregistered.clear()
        registered_paths = {song["path"] for song in load_songs_from_database()}
        
        for filename in os.listdir(self.current_folder):
            if filename.lower().endswith('.mp3'):
                file_path = os.path.join(self.current_folder, filename)
                if file_path not in registered_paths:
                    self.list_unregistered.addItem(filename)

    def filter_registered_songs(self):
        filter_text = self.filter_input.text().lower()
        for row in range(self.table_registered.rowCount()):
            hidden = True
            for col in range(self.table_registered.columnCount()):
                item = self.table_registered.item(row, col)
                if item and filter_text in item.text().lower():
                    hidden = False
                    break
            self.table_registered.setRowHidden(row, hidden)

    def edit_selected_songs(self):
        selected_rows = sorted(set(item.row() for item in self.table_registered.selectedItems()))
        if not selected_rows:
            return

        # Get selected songs data
        songs_to_edit = []
        for row in selected_rows:
            song_id = self.table_registered.item(row, 1).text()
            songs = load_songs_from_database()
            song = next((s for s in songs if s["id"] == song_id), None)
            if song:
                # Add order information
                song["order"] = get_playlist_order(self.current_folder, song_id)
                songs_to_edit.append(song)

        if not songs_to_edit:
            return

        dialog = EditDialog(songs_to_edit, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            values = dialog.get_values()
            self.apply_edits(songs_to_edit, values)

    def apply_edits(self, songs_to_edit, values):
        all_songs = load_songs_from_database()
        
        try:
            for song in songs_to_edit:
                db_song = next(s for s in all_songs if s["id"] == song["id"])
                db_song["series"] = values["series"]
                db_song["weight"] = values["weight"]

                if len(songs_to_edit) == 1 and "filename" in values:
                    old_path = song["path"]
                    new_filename = values["filename"]
                    new_path = os.path.join(os.path.dirname(old_path), new_filename)

                    if new_filename != os.path.basename(old_path):
                        os.rename(old_path, new_path)
                        db_song["path"] = new_path
                        db_song["name"] = new_filename

                        # Update title metadata to match filename without extension
                        try:
                            audio = EasyID3(new_path)
                        except ID3NoHeaderError:
                            audio = EasyID3()
                            audio.save(new_path)
                        
                        title_without_ext = os.path.splitext(new_filename)[0]
                        audio['title'] = title_without_ext
                        audio.save()

            save_songs_to_database(all_songs)
            self.refresh_all_views()
            self.statusBar().showMessage("Changes applied successfully")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error",
                f"An error occurred while applying changes: {str(e)}"
            )
            self.refresh_all_views()

    def remove_selected_songs(self):
        selected_rows = sorted(set(item.row() for item in self.table_registered.selectedItems()), reverse=True)
        if not selected_rows:
            return
            
        reply = QtWidgets.QMessageBox.question(
            self, 'Confirm Removal',
            'Are you sure you want to remove the selected songs?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            for row in selected_rows:
                song_id = self.table_registered.item(row, 1).text()
                file_path = self.table_registered.item(row, 3).text()
                
                try:
                    # Remove COMM tags from the file
                    audio = ID3(file_path)
                    audio.delall("COMM")
                    audio.save()
                except Exception as e:
                    print(f"Error removing metadata from {file_path}: {str(e)}")
                
                # Remove from both databases
                remove_song_from_database(song_id, self.current_folder)

            self.refresh_all_views()
            self.statusBar().showMessage("Selected songs removed successfully")

    def add_selected_songs(self):
        selected_items = self.list_unregistered.selectedItems()
        if not selected_items:
            return
            
        successful_adds = 0
        for item in selected_items:
            file_path = os.path.join(self.current_folder, item.text())
            
            # First check if the file has an ID in its metadata
            existing_id = get_id_from_metadata(file_path)
            if existing_id:
                # Check if this ID exists in our database
                songs = load_songs_from_database()
                existing_song = next((song for song in songs if song["id"] == existing_id), None)
                if existing_song:
                    # Update the existing entry if needed
                    existing_song["path"] = file_path
                    existing_song["name"] = os.path.basename(file_path)
                    save_songs_to_database(songs)
                    successful_adds += 1
                    continue
            
            # If no existing ID or invalid ID, create new entry
            if add_song_to_database(file_path):
                successful_adds += 1
        
        self.refresh_all_views()
        self.statusBar().showMessage(f"Added {successful_adds} songs successfully")

    def delete_playlist(self):
        """Delete the current playlist folder and its associated data"""
        if not self.current_folder:
            self.statusBar().showMessage("No folder selected")
            return
            
        # Show confirmation dialog
        reply = QtWidgets.QMessageBox.warning(
            self,
            'Delete Playlist',
            f'Are you sure you want to delete this playlist?\n\n'
            f'This will permanently delete:\n'
            f'- All files in {self.current_folder}\n'
            f'- Associated data in songs.json and playlists.json\n\n'
            'This action cannot be undone!',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                # Delete all files in the folder
                for root, dirs, files in os.walk(self.current_folder, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(self.current_folder)
                
                # Remove songs from songs.json
                songs = load_songs_from_database()
                songs = [song for song in songs 
                        if not song["path"].startswith(self.current_folder)]
                save_songs_to_database(songs)
                
                # Remove playlist from playlists.json
                playlists = load_playlists_from_database()
                playlists = [playlist for playlist in playlists 
                           if playlist["folder_path"] != self.current_folder]
                save_playlists_to_database(playlists)
                
                # Clear current folder and refresh UI
                self.current_folder = None
                self.folder_path.clear()
                self.refresh_all_views()
                self.statusBar().showMessage("Playlist deleted successfully")
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while deleting the playlist: {str(e)}"
                )
                self.refresh_all_views()


class OrderTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_changes = {}  # Store temporary order changes
        self.setup_ui()

    def setup_ui(self):
        # [Previous setup_ui code remains the same]
        layout = QtWidgets.QVBoxLayout(self)

        # Top controls
        controls_layout = QtWidgets.QHBoxLayout()
        
        # Change order controls
        order_layout = QtWidgets.QHBoxLayout()
        order_label = QtWidgets.QLabel("New Order:")
        self.order_spin = QtWidgets.QSpinBox()
        self.order_spin.setMinimum(1)
        self.set_order_button = QtWidgets.QPushButton("Set Order")
        self.set_order_button.clicked.connect(self.set_new_order)
        
        # Add Randomize button
        self.randomize_button = QtWidgets.QPushButton("Randomize")
        self.randomize_button.clicked.connect(self.randomize_songs)

        order_layout.addWidget(order_label)
        order_layout.addWidget(self.order_spin)
        order_layout.addWidget(self.set_order_button)
        order_layout.addWidget(self.randomize_button)  # Add randomize button to layout
        controls_layout.addLayout(order_layout)

        # Add enable and disable buttons
        enable_disable_layout = QtWidgets.QHBoxLayout()
        self.enable_button = QtWidgets.QPushButton("Enable Selected")
        self.enable_button.clicked.connect(self.enable_selected_songs)
        self.disable_button = QtWidgets.QPushButton("Disable Selected")
        self.disable_button.clicked.connect(self.disable_selected_songs)
        
        enable_disable_layout.addWidget(self.enable_button)
        enable_disable_layout.addWidget(self.disable_button)
        controls_layout.addLayout(enable_disable_layout)
        
        layout.addLayout(controls_layout)

        # Table for showing songs
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)  # Added Preview Order column
        self.table.setHorizontalHeaderLabels([
            "Current Order", "Preview Order", "ID", "Name", "Path", "Series", "Weight"
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.table)

        # Bottom controls for applying changes
        bottom_layout = QtWidgets.QHBoxLayout()
        
        # Method selection
        self.method_group = QtWidgets.QGroupBox("Apply Method")
        method_layout = QtWidgets.QHBoxLayout()
        self.current_dir_radio = QtWidgets.QRadioButton("Modify Current Directory")
        self.new_dir_radio = QtWidgets.QRadioButton("Copy to New Directory")
        self.current_dir_radio.setChecked(True)
        
        method_layout.addWidget(self.current_dir_radio)
        method_layout.addWidget(self.new_dir_radio)
        self.method_group.setLayout(method_layout)
        
        # Action buttons
        self.apply_button = QtWidgets.QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self.apply_changes)
        self.reset_button = QtWidgets.QPushButton("Reset Changes")
        self.reset_button.clicked.connect(self.reset_changes)
        
        bottom_layout.addWidget(self.method_group)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.reset_button)
        bottom_layout.addWidget(self.apply_button)
        
        layout.addLayout(bottom_layout)

    def refresh_view(self):
        if not self.parent.current_folder:
            return

        self.table.setSortingEnabled(False)
        self.table.clearContents()
        
        # Get songs with their order information
        folder_songs = load_folder_songs(self.parent.current_folder)
        
        # Sort by order
        folder_songs.sort(key=lambda x: x.get("order", 0))
        
        # Update table
        self.table.setRowCount(len(folder_songs))
        self.order_spin.setMaximum(len(folder_songs))
        
        for row, song in enumerate(folder_songs):
            current_order = song.get("order", 0)
            preview_order = self.current_changes.get(song["id"], current_order)
            
            # Create items for all columns
            order_item = QtWidgets.QTableWidgetItem()
            order_item.setData(QtCore.Qt.DisplayRole, current_order)
            
            preview_item = QtWidgets.QTableWidgetItem()
            id_item = QtWidgets.QTableWidgetItem(song["id"])
            name_item = QtWidgets.QTableWidgetItem(song["name"])
            path_item = QtWidgets.QTableWidgetItem(song["path"])
            series_item = QtWidgets.QTableWidgetItem(song["series"])
            weight_item = QtWidgets.QTableWidgetItem(str(song["weight"]))
            
            # Set items in table
            self.table.setItem(row, 0, order_item)
            self.table.setItem(row, 1, preview_item)
            self.table.setItem(row, 2, id_item)
            self.table.setItem(row, 3, name_item)
            self.table.setItem(row, 4, path_item)
            self.table.setItem(row, 5, series_item)
            self.table.setItem(row, 6, weight_item)

            # Handle display and styling for preview order
            if preview_order == -1:  # Disabled status
                preview_item.setData(QtCore.Qt.DisplayRole, "Disabled")
                light_gray = QtGui.QColor(245, 245, 245)  # Light gray background
                for col in range(7):
                    self.table.item(row, col).setBackground(light_gray)
            else:
                preview_item.setData(QtCore.Qt.DisplayRole, preview_order)
                if preview_order != current_order:
                    light_yellow = QtGui.QColor(255, 255, 200)  # Light yellow background
                    preview_item.setBackground(light_yellow)

        self.table.setSortingEnabled(True)
        self.apply_button.setEnabled(bool(self.current_changes))
        self.reset_button.setEnabled(bool(self.current_changes))

    def set_new_order(self):
        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))
        if not selected_rows:
            return
            
        new_order = self.order_spin.value()
        folder_songs = load_folder_songs(self.parent.current_folder)
        
        # Get selected song IDs
        selected_song_ids = [self.table.item(row, 2).text() for row in selected_rows]
        
        # First, preserve currently disabled songs
        disabled_songs = {
            song_id: order for song_id, order in self.current_changes.items()
            if order == -1 and song_id not in selected_song_ids
        }
        
        # Update preview orders for selected songs
        for song_id in selected_song_ids:
            self.current_changes[song_id] = new_order
            new_order += 1
        
        # Update other songs' preview orders, skipping disabled ones
        max_order = len(folder_songs)
        current_pos = 1
        
        for song in folder_songs:
            if song["id"] not in selected_song_ids and song["id"] not in disabled_songs:
                while current_pos in [self.current_changes.get(sid) for sid in selected_song_ids]:
                    current_pos += 1
                if current_pos <= max_order:
                    self.current_changes[song["id"]] = current_pos
                    current_pos += 1
        
        # Restore disabled songs
        self.current_changes.update(disabled_songs)
        
        self.refresh_view()

    def randomize_songs(self):
        """Handle the randomization of songs in the current folder"""
        if not self.parent.current_folder:
            return

        # Get current folder songs
        folder_songs = load_folder_songs(self.parent.current_folder)
        
        # Filter out disabled songs (those with order -1)
        active_songs = [
            song for song in folder_songs
            if self.current_changes.get(song['id'], song.get('order', 0)) != -1
        ]

        if not active_songs:
            return

        # Randomize the playlist
        randomized_songs = self.randomize_playlist(active_songs)

        # Update the current_changes dictionary with new orders
        for new_order, song in enumerate(randomized_songs, start=1):
            self.current_changes[song['id']] = new_order

        # Refresh the view to show the new ordering
        self.refresh_view()

    def randomize_playlist(self, songs):
        """
        Randomizes a playlist while maintaining even distribution of series,
        balancing between large and small series throughout the playlist.
        
        :param songs: List of dictionaries, each with 'series' and other metadata
        :return: List of shuffled songs
        """
        # Group songs by series and get series sizes
        series_dict = defaultdict(list)
        for song in songs:
            series_dict[song['series']].append(song)
        
        # Calculate target distribution for each series
        total_songs = len(songs)
        distribution_points = {}
        for series, series_songs in series_dict.items():
            # Calculate roughly how many slots we want between each song
            series_size = len(series_songs)
            distribution_points[series] = [
                int((i * total_songs) / series_size) 
                for i in range(series_size)
            ]
            # Add some randomness to the distribution points while maintaining order
            for i in range(len(distribution_points[series])):
                shift = random.randint(-2, 2)  # Small random shift
                distribution_points[series][i] = max(0, min(
                    total_songs - 1,
                    distribution_points[series][i] + shift
                ))
        
        # Shuffle songs within each series
        for series_songs in series_dict.values():
            random.shuffle(series_songs)
        
        # Initialize result list and tracking variables
        result = [None] * total_songs  # Pre-allocate list with None
        used_positions = set()
        series_index = {series: 0 for series in series_dict.keys()}
        
        # First pass: Place songs near their target positions
        for series in series_dict.keys():
            songs_to_place = series_dict[series]
            target_points = distribution_points[series]
            
            for i, target in enumerate(target_points):
                if i >= len(songs_to_place):
                    break
                    
                # Look for the closest available position to the target
                search_radius = 0
                while search_radius < total_songs:
                    for offset in [0, 1, -1]:  # Try target, then adjacent positions
                        pos = target + (offset * search_radius)
                        if 0 <= pos < total_songs and pos not in used_positions:
                            # Check if adjacent positions don't have same series
                            adjacent_clear = True
                            for adj in [pos-1, pos+1]:
                                if (0 <= adj < total_songs and 
                                    result[adj] is not None and 
                                    result[adj]['series'] == songs_to_place[i]['series']):
                                    adjacent_clear = False
                                    break
                            
                            if adjacent_clear:
                                result[pos] = songs_to_place[i]
                                used_positions.add(pos)
                                break
                    if pos in used_positions:  # If we placed a song, break the radius loop
                        break
                    search_radius += 1
        
        # Second pass: Fill any remaining gaps
        remaining_songs = []
        for series, songs in series_dict.items():
            remaining_songs.extend(
                song for song in songs 
                if song not in result
            )
        
        # Shuffle remaining songs
        random.shuffle(remaining_songs)
        
        # Fill gaps
        for i in range(total_songs):
            if result[i] is None and remaining_songs:
                # Find a remaining song that doesn't create adjacent series
                for j, song in enumerate(remaining_songs):
                    adjacent_clear = True
                    for adj in [i-1, i+1]:
                        if (0 <= adj < total_songs and 
                            result[adj] is not None and 
                            result[adj]['series'] == song['series']):
                            adjacent_clear = False
                            break
                    
                    if adjacent_clear:
                        result[i] = song
                        remaining_songs.pop(j)
                        break
        
        # Final pass: If any positions are still None, fill them with any remaining songs
        for i in range(total_songs):
            if result[i] is None and remaining_songs:
                result[i] = remaining_songs.pop(0)
        
        return [song for song in result if song is not None]

    def enable_selected_songs(self):
        """Enable selected songs and assign them new order numbers at the end"""
        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))
        if not selected_rows:
            return
        
        # Get selected song IDs and their current preview orders
        selected_songs = [
            (self.table.item(row, 2).text(),  # ID
            self.current_changes.get(
                self.table.item(row, 2).text(),  # Get preview order
                int(self.table.item(row, 0).text())  # Fallback to current order
            ))
            for row in selected_rows
        ]
        
        # Filter out songs that are not disabled (preview order != -1)
        disabled_songs = [(song_id, order) for song_id, order in selected_songs if order == -1]
        if not disabled_songs:
            return  # Exit if no disabled songs were selected
        
        # Find the highest current order number (excluding disabled songs)
        folder_songs = load_folder_songs(self.parent.current_folder)
        current_orders = []
        for song in folder_songs:
            preview_order = self.current_changes.get(song["id"], song.get("order", 0))
            if preview_order != -1:  # Only consider enabled songs
                current_orders.append(preview_order)
        
        next_order = max(current_orders, default=0) + 1
        
        # Enable only the disabled songs and assign them consecutive order numbers
        for song_id, _ in disabled_songs:
            self.current_changes[song_id] = next_order
            next_order += 1
        
        self.refresh_view()
    
    def disable_selected_songs(self):
        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))
        if not selected_rows:
            return
        
        # Get selected song IDs and their current orders
        selected_songs = [(self.table.item(row, 2).text(),  # ID
                          int(self.table.item(row, 0).text()))  # Current order
                         for row in selected_rows]
        
        # Mark selected songs as disabled in preview
        for song_id, _ in selected_songs:
            self.current_changes[song_id] = -1
        
        # Reorder remaining songs
        folder_songs = load_folder_songs(self.parent.current_folder)
        current_pos = 1
        
        for song in folder_songs:
            if song["id"] not in [s[0] for s in selected_songs]:
                if current_pos != song.get("order", 0):  # Only update if order changes
                    self.current_changes[song["id"]] = current_pos
                current_pos += 1
        
        self.refresh_view()

    def reset_changes(self):
        self.current_changes.clear()
        self.refresh_view()

    def apply_changes(self):
        if not self.current_changes:
            return

        try:
            current_dir = self.parent.current_folder
            target_dir = current_dir
            disabled_folder = os.path.join(current_dir, "Disabled")
            
            if self.new_dir_radio.isChecked():
                target_dir = QtWidgets.QFileDialog.getExistingDirectory(
                    self, "Select New Directory", current_dir
                )
                if not target_dir:
                    return
                os.makedirs(target_dir, exist_ok=True)
            else:
                os.makedirs(disabled_folder, exist_ok=True)
            
            songs = load_songs_from_database()
            new_songs = []  # Track new songs to be added
            
            # Process each song in the current directory
            for song in songs:
                if os.path.dirname(song["path"]) == current_dir:
                    old_path = song["path"]
                    filename = os.path.basename(old_path)
                    
                    # Extract original filename without order prefix
                    match = ORDER_PATTERN.match(filename)
                    original_name = match.group(2) if match else filename
                    
                    # Get the new order, checking both current_changes and existing order
                    current_order = get_playlist_order(current_dir, song["id"])
                    new_order = self.current_changes.get(song["id"], current_order)
                    
                    # Check if the song is disabled in current_changes
                    is_disabled = new_order == -1 or (
                        song["id"] not in self.current_changes and 
                        current_order == -1
                    )
                    
                    if is_disabled:  # Disabled song
                        if self.new_dir_radio.isChecked():
                            continue  # Skip disabled songs when copying to new directory
                        else:
                            # Move to Disabled folder, keeping original filename
                            new_path = os.path.join(disabled_folder, filename)
                            shutil.move(old_path, new_path)
                            song["path"] = new_path
                    else:
                        # Create new filename with updated order
                        new_filename = f"{new_order:03d} {original_name}"
                        
                        if self.new_dir_radio.isChecked():
                            # Copy file to new location with new filename
                            new_path = os.path.join(target_dir, new_filename)
                            shutil.copy2(old_path, new_path)
                            
                            # Generate a new unique ID considering both existing and new songs
                            used_ids = {s["id"] for s in songs}.union({s["id"] for s in new_songs})
                            new_id = None
                            for i in range(10000):
                                candidate_id = f"{ID_PREFIX}{i:04d}"
                                if candidate_id not in used_ids:
                                    new_id = candidate_id
                                    break
                            
                            if new_id is None:
                                raise ValueError("No available IDs left.")
                            
                            # Create new song entry
                            new_song = {
                                "id": new_id,
                                "name": new_filename,
                                "path": new_path,
                                "series": song["series"],
                                "weight": song["weight"]
                            }
                            new_songs.append(new_song)
                            
                            # Add ID to the new file's metadata
                            add_id_to_metadata(new_path, new_id)
                            
                            # Update title metadata for the new file
                            try:
                                audio = EasyID3(new_path)
                            except ID3NoHeaderError:
                                audio = EasyID3()
                                audio.save(new_path)
                            
                            # Set title with order prefix and without extension
                            title_with_order = os.path.splitext(new_filename)[0]
                            audio['title'] = title_with_order
                            audio.save()
                            
                            # Update order in the new directory with the new ID
                            update_playlist_order(target_dir, new_id, new_order)
                        else:
                            # Rename file in current directory
                            new_path = os.path.join(current_dir, new_filename)
                            os.rename(old_path, new_path)
                            song["path"] = new_path
                            song["name"] = new_filename
                            
                            # Update title metadata
                            try:
                                audio = EasyID3(new_path)
                            except ID3NoHeaderError:
                                audio = EasyID3()
                                audio.save(new_path)
                            
                            # Set title with order prefix and without extension
                            title_with_order = os.path.splitext(new_filename)[0]
                            audio['title'] = title_with_order
                            audio.save()
                            
                            # Update order in current directory
                            update_playlist_order(current_dir, song["id"], new_order)
            
            # Add all new songs to the database at once
            if new_songs:
                songs.extend(new_songs)
            
            # Save changes to database
            save_songs_to_database(songs)
            
            # If new directory was created, switch to it
            if self.new_dir_radio.isChecked():
                self.parent.current_folder = target_dir
                self.parent.folder_path.setText(target_dir)
            
            # Reset changes and refresh views
            self.current_changes.clear()
            self.parent.refresh_all_views()
            self.parent.statusBar().showMessage("Order changes applied successfully")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error",
                f"An error occurred while applying changes: {str(e)}"
            )
            self.parent.refresh_all_views()


class DisabledTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Table for showing disabled songs
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Path", "Series", "Weight", "Original Order"
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.table)
        
        # Enable button
        self.enable_button = QtWidgets.QPushButton("Enable Selected")
        self.enable_button.clicked.connect(self.enable_selected_songs)
        layout.addWidget(self.enable_button)

    def refresh_view(self):
        if not self.parent.current_folder:
            return
            
        disabled_folder = os.path.join(self.parent.current_folder, "Disabled")
        if not os.path.exists(disabled_folder):
            self.table.setRowCount(0)
            return
            
        # Get disabled songs
        songs = load_songs_from_database()
        disabled_songs = [
            song for song in songs 
            if os.path.dirname(song["path"]) == disabled_folder
        ]
        
        self.table.setRowCount(len(disabled_songs))
        for row, song in enumerate(disabled_songs):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(song["id"]))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(song["name"]))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(song["path"]))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(song["series"]))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(song["weight"])))
            
            # Get original order if available
            original_order = get_playlist_order(disabled_folder, song["id"])
            self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(str(original_order)))

    def enable_selected_songs(self):
        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))
        if not selected_rows:
            return
            
        try:
            songs = load_songs_from_database()
            current_dir = self.parent.current_folder
            disabled_folder = os.path.join(current_dir, "Disabled")
            
            # Get current max order from active (non-disabled) songs
            current_max_order = 0
            playlists = load_playlists_from_database()
            playlist_entry = next(
                (p for p in playlists if p["folder_path"] == current_dir),
                None
            )
            if playlist_entry:
                # Only consider orders of songs that are not in the Disabled folder
                active_song_ids = {s["id"] for s in songs 
                                if os.path.dirname(s["path"]) == current_dir}
                current_max_order = max(
                    (o["order"] for o in playlist_entry["orders"]
                    if o["id"] in active_song_ids),
                    default=0
                )
            
            # Process each selected song
            for row in selected_rows:
                song_id = self.table.item(row, 0).text()
                song = next((s for s in songs if s["id"] == song_id), None)
                
                if song:
                    # Move file back to main folder
                    old_path = song["path"]
                    filename = os.path.basename(old_path)
                    new_path = os.path.join(current_dir, filename)
                    
                    # Use shutil.move and handle file removal
                    if os.path.exists(old_path):
                        shutil.move(old_path, new_path)
                        # If original file still exists after move, delete it
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    
                    song["path"] = new_path
                    
                    # Assign new order (next number after current max)
                    current_max_order += 1
                    update_playlist_order(current_dir, song_id, current_max_order)
            
            save_songs_to_database(songs)
            self.parent.refresh_all_views()
            self.parent.statusBar().showMessage("Selected songs enabled successfully")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error",
                f"An error occurred while enabling songs: {str(e)}"
            )
            self.parent.refresh_all_views()


def extract_order_number(filename):
    """
    Extract the order number from a filename.
    Expected format: '###_filename' or '### filename'
    Returns 0 if no order number is found.
    """
    ORDER_PATTERN = re.compile(r'^(\d{3})\s+(.+)$')
    match = ORDER_PATTERN.match(filename)
    if match:
        return int(match.group(1))
    return 0

def initialize_database():
    """Initialize both database files if they don't exist"""
    if not os.path.exists(SONGS_DATABASE):
        with open(SONGS_DATABASE, "w") as db_file:
            json.dump([], db_file)
    
    if not os.path.exists(PLAYLISTS_DATABASE):
        with open(PLAYLISTS_DATABASE, "w") as db_file:
            json.dump([], db_file)

def load_songs_from_database():
    """Load song metadata from the main database"""
    with open(SONGS_DATABASE, "r") as db_file:
        return json.load(db_file)

def save_songs_to_database(songs):
    """Save song metadata to the main database"""
    with open(SONGS_DATABASE, "w") as db_file:
        json.dump(songs, db_file, indent=4)

def load_playlists_from_database():
    """Load playlist order information"""
    with open(PLAYLISTS_DATABASE, "r") as db_file:
        return json.load(db_file)

def save_playlists_to_database(playlists):
    """Save playlist order information"""
    with open(PLAYLISTS_DATABASE, "w") as db_file:
        json.dump(playlists, db_file, indent=4)

def get_playlist_order(folder_path, song_id):
    """Get the order of a song in a specific folder"""
    playlists = load_playlists_from_database()
    for playlist in playlists:
        if playlist["folder_path"] == folder_path:
            for order_entry in playlist["orders"]:
                if order_entry["id"] == song_id:
                    return order_entry["order"]
    return 0

def update_playlist_order(folder_path, song_id, new_order):
    """Update or add a song's order in a playlist"""
    playlists = load_playlists_from_database()
    
    # Find or create playlist entry
    playlist_entry = next(
        (p for p in playlists if p["folder_path"] == folder_path),
        None
    )
    
    if playlist_entry is None:
        playlist_entry = {
            "folder_path": folder_path,
            "orders": []
        }
        playlists.append(playlist_entry)
    
    # Update or add order
    order_entry = next(
        (o for o in playlist_entry["orders"] if o["id"] == song_id),
        None
    )
    
    if order_entry:
        order_entry["order"] = new_order
    else:
        playlist_entry["orders"].append({
            "id": song_id,
            "order": new_order
        })
    
    save_playlists_to_database(playlists)

def generate_song_id():
    songs = load_songs_from_database()
    used_ids = {song["id"] for song in songs}
    for i in range(10000):
        candidate_id = f"{ID_PREFIX}{i:04d}"
        if candidate_id not in used_ids:
            return candidate_id
    raise ValueError("No available IDs left.")

def find_next_available_order(songs, folder_path, current_max_order):
    """
    Find the next available order number in a sequence, filling any gaps.
    Returns the next available number.
    """
    # Get all order numbers in the folder
    folder_songs = [song for song in songs if os.path.dirname(song["path"]) == folder_path]
    used_numbers = set(extract_order_number(song["name"]) for song in folder_songs)
    
    # Start from 1 and find the first available number
    for i in range(1, current_max_order + 2):  # +2 to also check one number after max
        if i not in used_numbers:
            return i
    
    # If no gaps found, return next number after max
    return current_max_order + 1

def add_song_to_database(file_path):
    """Add a song to the database and its metadata."""
    try:
        songs = load_songs_from_database()
        if not any(song["path"] == file_path for song in songs):
            new_id = generate_song_id()
            current_folder = os.path.dirname(file_path)
            
            # Get current max order number for the folder
            current_max_order = 0
            playlists = load_playlists_from_database()
            playlist_entry = next(
                (p for p in playlists if p["folder_path"] == current_folder),
                None
            )
            
            if playlist_entry:
                current_max_order = max(
                    (o["order"] for o in playlist_entry["orders"]),
                    default=0
                )
            
            # Get the original name
            original_name = os.path.basename(file_path)
            
            # Create new song entry
            new_order = current_max_order + 1
            
            # Add ID to metadata
            if add_id_to_metadata(file_path, new_id):
                try:
                    # Update title metadata
                    audio = EasyID3(file_path)
                except ID3NoHeaderError:
                    audio = EasyID3()
                    audio.save(file_path)
                
                # Add to songs database
                new_song = {
                    "id": new_id,
                    "name": original_name,
                    "path": file_path,
                    "series": "",
                    "weight": 2
                }
                songs.append(new_song)
                save_songs_to_database(songs)
                
                # Add to playlists database
                update_playlist_order(current_folder, new_id, new_order)
                return True
        return False
    except Exception as e:
        print(f"Error adding song to database: {str(e)}")
        return False

def load_folder_songs(folder_path):
    """Load songs for a specific folder with their order information"""
    songs = load_songs_from_database()
    folder_songs = [
        song for song in songs 
        if os.path.dirname(song["path"]) == folder_path
    ]
    
    # Add order information from playlists database
    playlists = load_playlists_from_database()
    playlist_entry = next(
        (p for p in playlists if p["folder_path"] == folder_path),
        None
    )
    
    if playlist_entry:
        for song in folder_songs:
            order_entry = next(
                (o for o in playlist_entry["orders"] if o["id"] == song["id"]),
                None
            )
            song["order"] = order_entry["order"] if order_entry else 0
    else:
        # If no playlist entry exists, assign sequential orders
        for i, song in enumerate(folder_songs, 1):
            song["order"] = i
    
    return folder_songs

def apply_order_changes(current_folder, changes, target_folder=None):
    """Apply order changes to a folder"""
    if not target_folder:
        target_folder = current_folder
    
    playlists = load_playlists_from_database()
    
    # Find or create playlist entry for target folder
    target_playlist = next(
        (p for p in playlists if p["folder_path"] == target_folder),
        None
    )
    
    if target_playlist is None:
        target_playlist = {
            "folder_path": target_folder,
            "orders": []
        }
        playlists.append(target_playlist)
    
    # Update orders
    for song_id, new_order in changes.items():
        order_entry = next(
            (o for o in target_playlist["orders"] if o["id"] == song_id),
            None
        )
        
        if order_entry:
            order_entry["order"] = new_order
        else:
            target_playlist["orders"].append({
                "id": song_id,
                "order": new_order
            })
    
    save_playlists_to_database(playlists)

def remove_song_from_database(song_id, folder_path):
    """Remove a song from both databases"""
    # Remove from songs database
    songs = load_songs_from_database()
    songs = [song for song in songs if song["id"] != song_id]
    save_songs_to_database(songs)
    
    # Remove from playlists database
    playlists = load_playlists_from_database()
    for playlist in playlists:
        if playlist["folder_path"] == folder_path:
            playlist["orders"] = [
                o for o in playlist["orders"] 
                if o["id"] != song_id
            ]
    
    save_playlists_to_database(playlists)

def main():
    initialize_database()
    app = QtWidgets.QApplication([])
    window = PlaylistManagerUI()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()