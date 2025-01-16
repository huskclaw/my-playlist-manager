import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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

# Add songs from a folder to the database
def add_songs_from_folder(folder_path):
    songs = load_songs_from_database()
    existing_paths = {song["path"] for song in songs}

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and file_path not in existing_paths:
            new_song = {
                "id": generate_song_id(),
                "name": filename,
                "path": file_path,
                "series": "",
                "weight": 0
            }
            songs.append(new_song)
    save_songs_to_database(songs)

# UI code
class PlaylistManagerUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Playlist Manager")
        self.geometry("800x600")
        self.notebook = ttk.Notebook(self)

        # Tabs
        self.tab_registered = ttk.Frame(self.notebook)
        self.tab_unregistered = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_registered, text="Registered Songs")
        self.notebook.add(self.tab_unregistered, text="Unregistered Songs")
        self.notebook.pack(fill="both", expand=True)

        # Setup tabs
        self.setup_registered_tab()
        self.setup_unregistered_tab()

    def setup_registered_tab(self):
        columns = ("id", "name", "path", "series", "weight")
        self.tree_registered = ttk.Treeview(self.tab_registered, columns=columns, show="headings")
        for col in columns:
            self.tree_registered.heading(col, text=col.capitalize())
            self.tree_registered.column(col, width=150)
        self.tree_registered.pack(fill="both", expand=True)
        self.load_registered_songs()

    def load_registered_songs(self):
        for item in self.tree_registered.get_children():
            self.tree_registered.delete(item)
        songs = load_songs_from_database()
        for song in songs:
            self.tree_registered.insert("", "end", values=(song["id"], song["name"], song["path"], song["series"], song["weight"]))

    def setup_unregistered_tab(self):
        self.label_folder = ttk.Label(self.tab_unregistered, text="Select a folder to scan for songs:")
        self.label_folder.pack(pady=5)

        self.button_browse = ttk.Button(self.tab_unregistered, text="Browse", command=self.browse_folder)
        self.button_browse.pack(pady=5)

        self.list_unregistered = tk.Listbox(self.tab_unregistered)
        self.list_unregistered.pack(fill="both", expand=True)

        self.button_add = ttk.Button(self.tab_unregistered, text="Add Selected", command=self.add_selected_songs)
        self.button_add.pack(pady=5)

    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.list_unregistered.delete(0, tk.END)
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    self.list_unregistered.insert(tk.END, file_path)

    def add_selected_songs(self):
        selected_songs = self.list_unregistered.curselection()
        for index in selected_songs:
            file_path = self.list_unregistered.get(index)
            add_songs_from_folder(os.path.dirname(file_path))
        self.load_registered_songs()
        messagebox.showinfo("Success", "Selected songs have been added.")

# Main function
def main():
    initialize_database()
    app = PlaylistManagerUI()
    app.mainloop()

if __name__ == "__main__":
    main()
