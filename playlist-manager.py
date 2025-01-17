import os
import json
from PyQt5 import QtWidgets, QtGui, QtCore
from mutagen.id3 import ID3, COMM, ID3NoHeaderError
from mutagen.easyid3 import EasyID3

# Constants for JSON database
DATABASE_FILE = "songs.json"
ID_PREFIX = "ID"
SUPPORTED_EXTENSIONS = {'.mp3'}  # Supported file extensions

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

class PlaylistManagerUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Playlist Manager")
        self.setGeometry(100, 100, 1000, 700)
        self.current_folder = None
        
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
        
        layout.addLayout(filter_layout)
        
        # Setup table
        self.table_registered = QtWidgets.QTableWidget()
        self.table_registered.setColumnCount(5)
        self.table_registered.setHorizontalHeaderLabels(["ID", "Name", "Path", "Series", "Weight"])
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
        
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.remove_button)
        layout.addLayout(button_layout)
        
        self.tab_registered.setLayout(layout)

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
        
        for row, song in enumerate(folder_songs):
            self.table_registered.insertRow(row)
            self.table_registered.setItem(row, 0, QtWidgets.QTableWidgetItem(song["id"]))
            self.table_registered.setItem(row, 1, QtWidgets.QTableWidgetItem(song["name"]))
            self.table_registered.setItem(row, 2, QtWidgets.QTableWidgetItem(song["path"]))
            self.table_registered.setItem(row, 3, QtWidgets.QTableWidgetItem(song["series"]))
            self.table_registered.setItem(row, 4, QtWidgets.QTableWidgetItem(str(song["weight"])))

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
            song_id = self.table_registered.item(row, 0).text()
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
                song_id = self.table_registered.item(row, 0).text()
                songs = [song for song in songs if song["id"] != song_id]
            
            save_songs_to_database(songs)
            self.refresh_all_views()
            self.statusBar().showMessage("Selected songs removed")

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

def add_song_to_database(file_path):
    """
    Add a song to the database and its metadata.
    Returns True if successful, False otherwise.
    """
    try:
        songs = load_songs_from_database()
        if not any(song["path"] == file_path for song in songs):
            new_id = generate_song_id()
            
            # First try to add the ID to metadata
            if add_id_to_metadata(file_path, new_id):
                new_song = {
                    "id": new_id,
                    "name": os.path.basename(file_path),
                    "path": file_path,
                    "series": "",
                    "weight": 5
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