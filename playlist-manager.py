import os
import json
import re
from PyQt5 import QtWidgets, QtGui, QtCore
from mutagen.id3 import ID3, COMM, ID3NoHeaderError
from mutagen.easyid3 import EasyID3

# Constants for JSON database
DATABASE_FILE = "songs.json"
ID_PREFIX = "ID"
SUPPORTED_EXTENSIONS = {'.mp3'}  # Supported file extensions

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
    def __init__(self, songs, single_mode=False, parent=None):
        super().__init__(parent)
        self.songs = songs
        self.single_mode = single_mode
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Edit Song Details")
        layout = QtWidgets.QVBoxLayout(self)

        # File name and title editing (only for single song mode)
        if self.single_mode:
            # Filename group
            filename_group = QtWidgets.QGroupBox("File Name")
            filename_layout = QtWidgets.QVBoxLayout()
            self.filename_edit = QtWidgets.QLineEdit(os.path.basename(self.songs[0]["path"]))
            filename_layout.addWidget(self.filename_edit)
            filename_group.setLayout(filename_layout)
            layout.addWidget(filename_group)

            # Title group
            title_group = QtWidgets.QGroupBox("Title Metadata")
            title_layout = QtWidgets.QVBoxLayout()
            self.title_edit = QtWidgets.QLineEdit()
            try:
                audio = EasyID3(self.songs[0]["path"])
                self.title_edit.setText(audio.get('title', [''])[0])
            except:
                self.title_edit.setText(os.path.splitext(os.path.basename(self.songs[0]["path"]))[0])
            title_layout.addWidget(self.title_edit)
            title_group.setLayout(title_layout)
            layout.addWidget(title_group)

        # Series editing (for all modes)
        series_group = QtWidgets.QGroupBox("Series")
        series_layout = QtWidgets.QVBoxLayout()
        self.series_edit = QtWidgets.QLineEdit(self.songs[0]["series"])
        series_layout.addWidget(self.series_edit)
        series_group.setLayout(series_layout)
        layout.addWidget(series_group)

        # Weight editing (for all modes)
        weight_group = QtWidgets.QGroupBox("Weight")
        weight_layout = QtWidgets.QVBoxLayout()
        self.weight_spin = QtWidgets.QSpinBox()
        self.weight_spin.setRange(1, 10)
        self.weight_spin.setValue(self.songs[0]["weight"])
        weight_layout.addWidget(self.weight_spin)
        weight_group.setLayout(weight_layout)
        layout.addWidget(weight_group)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        if not self.single_mode:
            msg = QtWidgets.QLabel(f"Editing {len(self.songs)} songs")
            msg.setStyleSheet("color: gray; font-style: italic;")
            layout.insertWidget(0, msg)

    def get_values(self):
        result = {
            "series": self.series_edit.text(),
            "weight": self.weight_spin.value()
        }
        if self.single_mode:
            result.update({
                "filename": self.filename_edit.text(),
                "title": self.title_edit.text()
            })
        return result

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

class PlaylistManagerUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Playlist Manager")
        self.setGeometry(100, 100, 1000, 700)
        self.current_folder = None
        self.order_locked = False  # New attribute for order locking
        
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
        
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_path)
        folder_layout.addWidget(self.browse_button)
        main_layout.addLayout(folder_layout)
        
        # Tabs
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self.tab_registered = QtWidgets.QWidget()
        self.tab_unregistered = QtWidgets.QWidget()
        
        self.tabs.addTab(self.tab_registered, "Registered Songs")
        self.tabs.addTab(self.tab_unregistered, "Unregistered Songs")
        
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
        
        # Add order lock toggle button
        self.order_lock_button = QtWidgets.QPushButton("Lock Order")
        self.order_lock_button.setCheckable(True)
        self.order_lock_button.clicked.connect(self.toggle_order_lock)
        filter_layout.addWidget(self.order_lock_button)
        
        layout.addLayout(filter_layout)
        
        # Setup table
        self.table_registered = QtWidgets.QTableWidget()
        self.table_registered.setColumnCount(6)  # Added Order column
        self.table_registered.setHorizontalHeaderLabels(["Order", "ID", "Name", "Path", "Series", "Weight"])
        self.table_registered.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table_registered.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_registered.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table_registered.setSortingEnabled(True)
        layout.addWidget(self.table_registered)
        
        # Add buttons for editing
        button_layout = QtWidgets.QHBoxLayout()
        self.edit_button = QtWidgets.QPushButton("Edit Selected")
        self.edit_button.clicked.connect(self.edit_selected_songs)
        self.remove_button = QtWidgets.QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected_songs)
        self.reorder_button = QtWidgets.QPushButton("Change Order")
        self.reorder_button.clicked.connect(self.change_order)
        self.reorder_button.setEnabled(False)  # Disabled by default
        
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.reorder_button)
        layout.addLayout(button_layout)
        
        self.tab_registered.setLayout(layout)

    def toggle_order_lock(self, checked):
        self.order_locked = checked
        self.reorder_button.setEnabled(checked)
        self.table_registered.setSortingEnabled(not checked)
        self.order_lock_button.setText("Unlock Order" if checked else "Lock Order")
        if checked:
            # When locking, ensure items are sorted by their current order
            self.table_registered.sortItems(0)  # Sort by Order column

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

    def load_registered_songs(self):
        if not self.current_folder:
            return
            
        self.table_registered.setRowCount(0)
        songs = load_songs_from_database()
        
        # Filter songs from current folder
        folder_songs = [song for song in songs if os.path.dirname(song["path"]) == self.current_folder]
        
        # Sort by stored order number first, then by filename order as backup
        folder_songs.sort(key=lambda x: (x.get("order", 0), self.extract_order_number(x["name"])))
        
        for row, song in enumerate(folder_songs):
            order_num = song.get("order", self.extract_order_number(song["name"]))
            self.table_registered.insertRow(row)
            self.table_registered.setItem(row, 0, QtWidgets.QTableWidgetItem(f"{order_num:03d}"))
            self.table_registered.setItem(row, 1, QtWidgets.QTableWidgetItem(song["id"]))
            self.table_registered.setItem(row, 2, QtWidgets.QTableWidgetItem(song["name"]))
            self.table_registered.setItem(row, 3, QtWidgets.QTableWidgetItem(song["path"]))
            self.table_registered.setItem(row, 4, QtWidgets.QTableWidgetItem(song["series"]))
            self.table_registered.setItem(row, 5, QtWidgets.QTableWidgetItem(str(song["weight"])))

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
                songs_to_edit.append(song)

        if not songs_to_edit:
            return

        # Determine if we're in single or multi mode
        single_mode = len(songs_to_edit) == 1
        if len(songs_to_edit) > 1 and single_mode:
            QtWidgets.QMessageBox.warning(
                self, "Warning",
                "File name and title can only be edited for a single song at a time. Please select only one song."
            )
            return

        # Show edit dialog
        dialog = EditDialog(songs_to_edit, single_mode, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            values = dialog.get_values()
            self.apply_edits(songs_to_edit, values)

    def apply_edits(self, songs_to_edit, values):
        all_songs = load_songs_from_database()
        
        try:
            for song in songs_to_edit:
                # Update database values
                db_song = next(s for s in all_songs if s["id"] == song["id"])
                db_song["series"] = values["series"]
                db_song["weight"] = values["weight"]

                # Handle single-song edits (filename and title)
                if len(songs_to_edit) == 1:
                    old_path = song["path"]
                    new_filename = values["filename"]
                    new_path = os.path.join(os.path.dirname(old_path), new_filename)

                    # Rename the file if name changed
                    if new_filename != os.path.basename(old_path):
                        os.rename(old_path, new_path)
                        db_song["path"] = new_path
                        db_song["name"] = new_filename

                    # Update title metadata
                    try:
                        audio = EasyID3(new_path)
                    except ID3NoHeaderError:
                        audio = EasyID3()
                        audio.save(new_path)
                    
                    audio['title'] = values["title"]
                    audio.save()

            # Save all changes to database
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
            songs = load_songs_from_database()
            for row in selected_rows:
                song_id = self.table_registered.item(row, 1).text()
                # Get the path before removing from database
                song_to_remove = next((song for song in songs if song["id"] == song_id), None)
                if song_to_remove:
                    file_path = song_to_remove["path"]
                    try:
                        # Remove COMM tags from the file
                        audio = ID3(file_path)
                        audio.delall("COMM")
                        audio.save()
                    except Exception as e:
                        print(f"Error removing metadata from {file_path}: {str(e)}")
                
                songs = [song for song in songs if song["id"] != song_id]

            # After removal, reorder remaining songs in the same folder
            if self.current_folder:
                folder_songs = [song for song in songs if os.path.dirname(song["path"]) == self.current_folder]
                folder_songs.sort(key=lambda x: extract_order_number(x["name"]))
                
                # Reassign order numbers
                for i, song in enumerate(folder_songs, 1):
                    old_name = song["name"]
                    if ORDER_PATTERN.match(old_name):
                        base_name = ORDER_PATTERN.match(old_name).group(2)
                    else:
                        base_name = old_name
                        
                    new_name = f"{i:03d} {base_name}"
                    old_path = song["path"]
                    new_path = os.path.join(os.path.dirname(old_path), new_name)
                    
                    # Update file name
                    try:
                        os.rename(old_path, new_path)
                        song["name"] = new_name
                        song["path"] = new_path
                        song["order"] = i
                        
                        # Update title metadata
                        try:
                            audio = EasyID3(new_path)
                        except ID3NoHeaderError:
                            audio = EasyID3()
                            audio.save(new_path)
                        
                        audio['title'] = os.path.splitext(new_name)[0]
                        audio.save()
                    except Exception as e:
                        print(f"Error updating file after removal: {str(e)}")
            
            save_songs_to_database(songs)
            self.refresh_all_views()
            self.statusBar().showMessage("Selected songs removed and order updated")

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

    def change_order(self):
        if not self.order_locked:
            return

        selected_rows = sorted(set(item.row() for item in self.table_registered.selectedItems()))
        if not selected_rows:
            return

        # Get the maximum possible order number
        max_order = self.table_registered.rowCount()

        # Show order dialog
        dialog = OrderDialog(max_order, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        new_order = dialog.get_order() - 1  # Convert to 0-based index
        
        # Get all current rows in order
        current_order = []
        for row in range(self.table_registered.rowCount()):
            row_data = []
            for col in range(self.table_registered.columnCount()):
                row_data.append(self.table_registered.item(row, col).text())
            current_order.append(row_data)

        # Remove selected rows from current order
        selected_rows_data = [current_order[row] for row in selected_rows]
        remaining_rows = [row for i, row in enumerate(current_order) if i not in selected_rows]

        # Insert selected rows at new position
        new_order = remaining_rows[:new_order] + selected_rows_data + remaining_rows[new_order:]

        # Update the table and file names
        self.apply_new_order(new_order)


    def apply_new_order(self, new_order):
        try:
            songs = load_songs_from_database()
            
            # Update each song's order
            for i, row_data in enumerate(new_order):
                song_id = row_data[1]  # ID is in column 1
                
                # Find the song in the database
                song = next(s for s in songs if s["id"] == song_id)
                
                # Update the order in database
                song["order"] = i + 1
                
                # Extract the non-order part of the name
                match = ORDER_PATTERN.match(song["name"])
                if not match:
                    continue
                    
                base_name = match.group(2)
                new_name = f"{i+1:03d} {base_name}"
                
                # Update file name
                old_path = song["path"]
                new_path = os.path.join(os.path.dirname(old_path), new_name + os.path.splitext(old_path)[1])
                
                # Rename the file
                os.rename(old_path, new_path)
                
                # Update database entry
                song["name"] = new_name
                song["path"] = new_path
                
                # Update title metadata
                try:
                    audio = EasyID3(new_path)
                except ID3NoHeaderError:
                    audio = EasyID3()
                    audio.save(new_path)
                
                audio['title'] = new_name.rsplit('.', 1)[0]  # Remove extension if present
                audio.save()
            
            # Save updated database
            save_songs_to_database(songs)
            
            # Refresh the view
            self.refresh_all_views()
            self.statusBar().showMessage("Order updated successfully")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error",
                f"An error occurred while updating order: {str(e)}"
            )
            self.refresh_all_views()

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
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "w") as db_file:
            json.dump([], db_file)

def load_songs_from_database():
    with open(DATABASE_FILE, "r") as db_file:
        return json.load(db_file)

def save_songs_to_database(songs):
    with open(DATABASE_FILE, "w") as db_file:
        json.dump(songs, db_file, indent=4)

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
    """
    Add a song to the database and its metadata.
    Returns True if successful, False otherwise.
    """
    try:
        songs = load_songs_from_database()
        if not any(song["path"] == file_path for song in songs):
            new_id = generate_song_id()
            current_folder = os.path.dirname(file_path)
            
            # Get current max order number for the folder
            current_max_order = 0
            for song in songs:
                if os.path.dirname(song["path"]) == current_folder:
                    order_num = extract_order_number(song["name"])
                    current_max_order = max(current_max_order, order_num)
            
            # Get the original name and any existing order number
            original_name = os.path.basename(file_path)
            original_order = extract_order_number(original_name)
            
            # If the original name has an order number, check if it's available
            if original_order > 0:
                # Check if this order number is already taken
                is_order_taken = any(
                    extract_order_number(song["name"]) == original_order 
                    for song in songs 
                    if os.path.dirname(song["path"]) == current_folder
                )
                
                if is_order_taken:
                    # Find the next available order number
                    new_order = find_next_available_order(songs, current_folder, current_max_order)
                else:
                    new_order = original_order
            else:
                # No original order number, just get next available
                new_order = find_next_available_order(songs, current_folder, current_max_order)
            
            # Remove any existing order number pattern and get clean name
            if ORDER_PATTERN.match(original_name):
                clean_name = ORDER_PATTERN.match(original_name).group(2)
            else:
                clean_name = original_name
            
            # Create new filename with new order
            new_name = f"{new_order:03d} {clean_name}"
            new_path = os.path.join(current_folder, new_name)
            
            # Rename the file first
            try:
                os.rename(file_path, new_path)
            except Exception as e:
                print(f"Error renaming file: {str(e)}")
                return False
            
            # Update the metadata (both ID and title)
            if add_id_to_metadata(new_path, new_id):
                try:
                    # Update title metadata
                    audio = EasyID3(new_path)
                except ID3NoHeaderError:
                    audio = EasyID3()
                    audio.save(new_path)
                
                # Set the title to match the new filename (without extension)
                audio['title'] = os.path.splitext(new_name)[0]
                audio.save()
                
                new_song = {
                    "id": new_id,
                    "name": new_name,
                    "path": new_path,
                    "series": "",
                    "weight": 5,
                    "order": new_order
                }
                songs.append(new_song)
                save_songs_to_database(songs)
                return True
        return False
    except Exception as e:
        print(f"Error adding song to database: {str(e)}")
        return False

def main():
    initialize_database()
    app = QtWidgets.QApplication([])
    window = PlaylistManagerUI()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()