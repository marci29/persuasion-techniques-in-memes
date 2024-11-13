import re
import os
import tkinter as tk
import xml.etree.ElementTree as ET
from tkinter import filedialog, Canvas, Scrollbar
from PIL import Image, ImageTk, ImageFile

# Allow loading truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Label-to-character mapping
LABEL_CHAR_DICT = {
    0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
    10: 'A', 11: 'B', 12: 'C', 13: 'D', 14: 'E', 15: 'F', 16: 'G', 17: 'H', 18: 'I',
    19: 'J', 20: 'K', 21: 'L', 22: 'M', 23: 'N', 24: 'O', 25: 'P', 26: 'Q', 27: 'R',
    28: 'S', 29: 'T', 30: 'U', 31: 'V', 32: 'W', 33: 'X', 34: 'Y', 35: 'Z', 36: 'a',
    37: 'b', 38: 'c', 39: 'd', 40: 'e', 41: 'f', 42: 'g', 43: 'h', 44: 'i', 45: 'j',
    46: 'k', 47: 'l', 48: 'm', 49: 'n', 50: 'o', 51: 'p', 52: 'q', 53: 'r', 54: 's',
    55: 't', 56: 'u', 57: 'v', 58: 'w', 59: 'x', 60: 'y', 61: 'z', 62: '"', 63: '&',
    64: '!', 65: '%', 66: "'", 67: '.', 68: '+', 69: '-', 70: ',', 71: '*', 72: '?', 73: '..'
}

class ImageAnnotatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Annotator")

        # UI elements
        self.load_dir_button = tk.Button(root, text="Load Directory (Ctrl+L)", command=self.load_directory)
        self.load_dir_button.pack()

        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = Canvas(self.canvas_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scroll_x = Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.scroll_y = Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)

        self.update_label_button = tk.Button(root, text="Update Label (Ctrl+S)", command=self.update_label)
        self.update_label_button.pack()

        self.image_label = tk.Label(root, text="No image loaded")
        self.image_label.pack()

        # Variables for managing directory, images, and bounding boxes
        self.directory = None
        self.images = []
        self.xml_files = []
        self.current_image_index = -1
        self.current_bbox_index = -1
        self.bboxes = []

        # Keyboard bindings
        self.root.bind('<Control-l>', lambda event: self.load_directory())
        self.root.bind('<Control-s>', lambda event: self.update_label())
        self.root.bind('<Left>', lambda event: self.prev_bbox())
        self.root.bind('<Right>', lambda event: self.next_bbox())
        self.root.bind('<Control-Left>', lambda event: self.prev_image())
        self.root.bind('<Control-Right>', lambda event: self.next_image())
        self.root.bind('<Up>', lambda event: self.change_label(1))  # Increase label
        self.root.bind('<Down>', lambda event: self.change_label(-1))  # Decrease label

    def load_directory(self):
        self.directory = filedialog.askdirectory()
        if not self.directory:
            return

        self.images = [f for f in os.listdir(self.directory) if f.endswith(('.jpg', '.png'))]
        self.xml_files = [f for f in os.listdir(self.directory) if f.endswith('.xml')]

        self.images.sort(key=self.extract_number)
        self.xml_files.sort(key=self.extract_number)

        self.current_image_index = 0
        self.load_image()

    def extract_number(self, filename):
        parts = re.findall(r'\d+', filename)
        if parts:
            return int(parts[0])
        return float('inf')

    def load_image(self):
        if self.current_image_index < 0 or self.current_image_index >= len(self.images):
            return

        image_path = os.path.join(self.directory, self.images[self.current_image_index])
        xml_path = os.path.join(self.directory, self.xml_files[self.current_image_index])

        self.image = Image.open(image_path)
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.config(scrollregion=(0, 0, self.tk_image.width(), self.tk_image.height()))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        self.load_bboxes(xml_path)
        self.current_bbox_index = 0
        self.show_bbox()
        self.image_label.config(text=f"Current Image: {self.images[self.current_image_index]}")

    def load_bboxes(self, xml_path):
        tree = ET.parse(xml_path)
        root = tree.getroot()

        self.bboxes = []
        for obj in root.findall('object'):
            bbox = obj.find('robndbox')
            cx = float(bbox.find('cx').text)
            cy = float(bbox.find('cy').text)
            w = float(bbox.find('w').text)
            h = float(bbox.find('h').text)
            label = int(obj.find('label').text)
            self.bboxes.append((cx, cy, w, h, label))

    def show_bbox(self):
        self.canvas.delete("bbox")

        img_width, img_height = self.image.size
        canvas_width, canvas_height = self.tk_image.width(), self.tk_image.height()

        x_scale = canvas_width / img_width
        y_scale = canvas_height / img_height

        for i, bbox in enumerate(self.bboxes):
            cx, cy, w, h, label = bbox
            char = LABEL_CHAR_DICT.get(label, "?")
            x1, y1 = (cx - w / 2) * x_scale, (cy - h / 2) * y_scale
            x2, y2 = (cx + w / 2) * x_scale, (cy + h / 2) * y_scale

            color = "red" if i == self.current_bbox_index else "blue"
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, tags="bbox")
            self.canvas.create_text(cx * x_scale, (cy - h / 2) * y_scale - 10, text=f"{label} ({char})", fill=color, tags="bbox")

    def update_label(self):
        if self.current_bbox_index < 0 or self.current_bbox_index >= len(self.bboxes):
            print("No bounding box selected.")
            return

        self.save_xml()
        self.show_bbox()

    def change_label(self, delta):
        if self.current_bbox_index < 0 or self.current_bbox_index >= len(self.bboxes):
            return

        cx, cy, w, h, label = self.bboxes[self.current_bbox_index]
        new_label = max(0, label + delta)
        self.bboxes[self.current_bbox_index] = (cx, cy, w, h, new_label)
        self.show_bbox()

    def save_xml(self):
        xml_path = os.path.join(self.directory, self.xml_files[self.current_image_index])
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for i, obj in enumerate(root.findall('object')):
            obj.find('label').text = str(self.bboxes[i][4])

        tree.write(xml_path)

    def prev_image(self):
        self.current_image_index -= 1
        if self.current_image_index < 0:
            self.current_image_index = len(self.images) - 1
        self.load_image()

    def next_image(self):
        self.current_image_index += 1
        if self.current_image_index >= len(self.images):
            self.current_image_index = 0
        self.load_image()

    def prev_bbox(self):
        self.current_bbox_index -= 1
        if self.current_bbox_index < 0:
            self.current_bbox_index = len(self.bboxes) - 1
        self.show_bbox()

    def next_bbox(self):
        self.current_bbox_index += 1
        if self.current_bbox_index >= len(self.bboxes):
            self.current_bbox_index = 0
        self.show_bbox()

# Main entry point
if __name__ == "__main__":
    root = tk.Tk()
    app = ImageAnnotatorApp(root)
    root.mainloop()
