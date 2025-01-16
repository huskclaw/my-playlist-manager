import os
import json
from PyQt5 import QtWidgets, QtGui, QtCore

# Constants for JSON database
DATABASE_FILE = "songs.json"
ID_PREFIX = "ID"

# Ensure the JSON database file exists
def initialize_database():
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "w") as db_file:
            json.dump([], db_file)

# Load songs from the database
def load_songs_from_database():
    with open(DATABASE_FILE, "r") as db_file:
        return json.load(db_file)

# Save songs to the database
def save_songs_to_database(songs):
    with open(DATABASE_FILE, "w") as db_file:
        json.dump(songs, db_file, indent=4)

# Generate a unique ID for a song
def generate_song_id():
    songs = load_songs_from_database()
    used_ids = {song["id"] for song in songs}
    for i in range(10000):
        candidate_id = f"{ID_PREFIX}{i:04d}"
        if candidate_id not in used_ids:
            return candidate_id
    raise ValueError("No available IDs left.")

# Check if a song is already in the database
def is_song_in_database(file_path):
    songs = load_songs_from_database()
    for song in songs:
        if song["path"] == file_path:
            return song
    return None

# Add a single song to the database
def add_song_to_database(file_path):
    if not is_song_in_database(file_path):
        new_song = {
            "id": generate_song_id(),
            "name": os.path.basename(file_path),
            "path": file_path,
            "series": "",
            "weight": 5
        }
        songs = load_songs_from_database()
        songs.append(new_song)
        save_songs_to_database(songs)

# UI code
class PlaylistManagerUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Playlist Manager")
        self.setGeometry(100, 100, 800, 600)

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tabs
        self.tab_registered = QtWidgets.QWidget()
        self.tab_unregistered = QtWidgets.QWidget()

        self.tabs.addTab(self.tab_registered, "Registered Songs")
        self.tabs.addTab(self.tab_unregistered, "Unregistered Songs")

        # Setup tabs
        self.setup_registered_tab()
        self.setup_unregistered_tab()

    def setup_registered_tab(self):
        layout = QtWidgets.QVBoxLayout()

        self.table_registered = QtWidgets.QTableWidget()
        self.table_registered.setColumnCount(5)
        self.table_registered.setHorizontalHeaderLabels(["ID", "Name", "Path", "Series", "Weight"])
        self.table_registered.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.table_registered)

        self.tab_registered.setLayout(layout)
        self.load_registered_songs()

    def load_registered_songs(self):
        self.table_registered.setRowCount(0)
        songs = load_songs_from_database()
        for row, song in enumerate(songs):
            self.table_registered.insertRow(row)
            self.table_registered.setItem(row, 0, QtWidgets.QTableWidgetItem(song["id"]))
            self.table_registered.setItem(row, 1, QtWidgets.QTableWidgetItem(song["name"]))
            self.table_registered.setItem(row, 2, QtWidgets.QTableWidgetItem(song["path"]))
            self.table_registered.setItem(row, 3, QtWidgets.QTableWidgetItem(song["series"]))
            self.table_registered.setItem(row, 4, QtWidgets.QTableWidgetItem(str(song["weight"])))

    def setup_unregistered_tab(self):
        layout = QtWidgets.QVBoxLayout()

        self.label_folder = QtWidgets.QLabel("Select a folder to scan for songs:")
        layout.addWidget(self.label_folder)

        self.button_browse = QtWidgets.QPushButton("Browse")
        self.button_browse.clicked.connect(self.browse_folder)
        layout.addWidget(self.button_browse)

        self.list_unregistered = QtWidgets.QListWidget()
        self.list_unregistered.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        layout.addWidget(self.list_unregistered)

        self.button_add = QtWidgets.QPushButton("Add Selected")
        self.button_add.clicked.connect(self.add_selected_songs)
        layout.addWidget(self.button_add)

        self.tab_unregistered.setLayout(layout)

    def browse_folder(self):
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.list_unregistered.clear()
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    song = is_song_in_database(file_path)
                    if song:
                        self.list_unregistered.addItem(f"[Registered: {song['id']}] {file_path}")
                    else:
                        next_id = generate_song_id()
                        self.list_unregistered.addItem(f"[Unregistered: {next_id}] {file_path}")

    def add_selected_songs(self):
        for item in self.list_unregistered.selectedItems():
            file_path = item.text().split('] ')[-1]
            if "Unregistered" in item.text():
                add_song_to_database(file_path)
        self.load_registered_songs()
        self.browse_folder()
        QtWidgets.QMessageBox.information(self, "Success", "Selected songs have been added.")

# Main function
def main():
    initialize_database()
    app = QtWidgets.QApplication([])
    window = PlaylistManagerUI()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()
