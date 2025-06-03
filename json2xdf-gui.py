import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os

def browse_json_file():
    """Opens a file dialog to select a JSON file."""
    filename = filedialog.askopenfilename(
        title="Select JSON File",
        filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
    )
    if filename:
        json_file_entry.delete(0, tk.END)
        json_file_entry.insert(0, filename)

def browse_xdf_file():
    """Opens a file dialog to select or name an XDF output file."""
    filename = filedialog.asksaveasfilename(
        title="Save XDF File As",
        filetypes=(("XDF files", "*.xdf"), ("All files", "*.*")),
        defaultextension=".xdf"
    )
    if filename:
        xdf_file_entry.delete(0, tk.END)
        xdf_file_entry.insert(0, filename)

def run_conversion():
    """Gets the input values and runs the json2xdf.py script."""
    json_file = json_file_entry.get()
    xdf_file = xdf_file_entry.get()
    base_offset = base_offset_entry.get()

    if not json_file:
        messagebox.showerror("Error", "Please select an input JSON file.")
        return
    if not xdf_file:
        messagebox.showerror("Error", "Please specify an output XDF file path.")
        return

    # Validate base_offset format (optional, but good practice)
    if base_offset:
        if not base_offset.startswith("0x"):
            messagebox.showerror("Error", "Base offset must be a hexadecimal value starting with '0x' (e.g., 0x200000).")
            return
        try:
            int(base_offset, 16)
        except ValueError:
            messagebox.showerror("Error", "Invalid hexadecimal value for base offset.")
            return
    else:
        # Default baseoffset if not provided, as per json2xdf.py
        base_offset = "0x0"


    # Assuming json2xdf.py is in the same directory as this GUI script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json2xdf_script_path = os.path.join(script_dir, "json2xdf.py")

    if not os.path.exists(json2xdf_script_path):
        # Fallback if json2xdf.py is not found in the same directory
        # Try to find it in the directory of aldee/a2l2xdf/
        # This path is based on the uploaded file structure
        # Modify this path if your actual structure is different
        base_project_dir = os.path.join(script_dir, "aldee", "a2l2xdf")
        specific_subdir_name = next((d for d in os.listdir(base_project_dir) if os.path.isdir(os.path.join(base_project_dir, d)) and "a2l2xdf-" in d), None)

        if specific_subdir_name:
            json2xdf_script_path = os.path.join(base_project_dir, specific_subdir_name, "json2xdf.py")
        else: # Final fallback if not found by guessing the path
            json2xdf_script_path = "json2xdf.py" # Assumes it's in PATH or current working dir


    if not os.path.exists(json2xdf_script_path) and not shutil.which("json2xdf.py"):
         messagebox.showerror("Error", f"json2xdf.py script not found at {json2xdf_script_path} or in system PATH. Please ensure it's accessible.")
         return

    command = ["python", json2xdf_script_path, json_file, xdf_file, "--baseoffset", base_offset]

    try:
        status_label.config(text="Running conversion...")
        root.update_idletasks() # Update GUI before blocking subprocess call

        # Run the script
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            messagebox.showinfo("Success", f"Conversion complete! XDF file saved to: {xdf_file}\n\nOutput:\n{stdout}")
            status_label.config(text="Conversion successful!")
        else:
            messagebox.showerror("Error", f"Conversion failed.\n\nError:\n{stderr}\n\nOutput:\n{stdout}")
            status_label.config(text="Conversion failed.")

    except FileNotFoundError:
        messagebox.showerror("Error", "Python interpreter not found. Please ensure Python is installed and in your PATH.")
        status_label.config(text="Error: Python not found.")
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        status_label.config(text=f"Error: {e}")

# --- Create the main window ---
root = tk.Tk()
root.title("JSON to XDF Converter GUI")

# --- Input JSON file ---
tk.Label(root, text="Input JSON File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
json_file_entry = tk.Entry(root, width=50)
json_file_entry.grid(row=0, column=1, padx=5, pady=5)
tk.Button(root, text="Browse...", command=browse_json_file).grid(row=0, column=2, padx=5, pady=5)

# --- Output XDF file ---
tk.Label(root, text="Output XDF File:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
xdf_file_entry = tk.Entry(root, width=50)
xdf_file_entry.grid(row=1, column=1, padx=5, pady=5)
tk.Button(root, text="Browse...", command=browse_xdf_file).grid(row=1, column=2, padx=5, pady=5)

# --- Base Offset ---
tk.Label(root, text="Base Offset (hex):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
base_offset_entry = tk.Entry(root, width=20)
base_offset_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
base_offset_entry.insert(0, "0x0") # Default value

# --- Run Button ---
run_button = tk.Button(root, text="Run Conversion", command=run_conversion)
run_button.grid(row=3, column=0, columnspan=3, pady=10)

# --- Status Label ---
status_label = tk.Label(root, text="")
status_label.grid(row=4, column=0, columnspan=3, pady=5)

# Start the GUI event loop
root.mainloop()