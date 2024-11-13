# Imports
import os
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw
from collections import defaultdict

#---------------------------------------------------------------------------------------------------

# Function to extract a number from the filename for sorting purposes
def extract_number(filename):

    # Find the number that appears just before the '.jpg' extension
    if filename.endswith('.jpg'):
        match = re.search(r'(\d{3,4})\.jpg$', filename)
    # Find the number that appears just before the '.txt' extension
    elif filename.endswith('.txt'):
        match = re.search(r'(\d{3,4})\.txt$', filename)
    # Find the number that appears just before the '.xml' extension
    elif filename.endswith('.xml'):
        match = re.search(r'(\d{3,4})\.xml$', filename)

    return int(match.group(1)) if match else float('inf')

#---------------------------------------------------------------------------------------------------

# Function to rename xml and jpg files in a folder to format xyz.jpg and xyz.xml
def rename_files_in_folder(folder_path, new_folder_path):
    images = sorted([f for f in os.listdir(folder_path) if f.lower().endswith('.jpg')])
    xmls = sorted([f for f in os.listdir(folder_path) if f.lower().endswith('.xml')])

    for i, (img_file, xml_file) in enumerate(zip(images, xmls), start=1):
        if i < 10:
            new_img_name = f"img00{i}.jpg"
            new_xml_name = f"img00{i}.xml"
        elif i < 100:
            new_img_name = f"img0{i}.jpg"
            new_xml_name = f"img0{i}.xml"
        else:
            new_img_name = f"img{i}.jpg"
            new_xml_name = f"img{i}.xml"
            
        img_path = os.path.join(folder_path, img_file)
        xml_path = os.path.join(folder_path, xml_file)

        new_img_path = os.path.join(new_folder_path, new_img_name)
        new_xml_path = os.path.join(new_folder_path, new_xml_name)

        os.rename(img_path, new_img_path)
        os.rename(xml_path, new_xml_path)

#---------------------------------------------------------------------------------------------------

# Function to parse xml to get main information for drawing bounding boxes
def parse_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    char_boxes = []
    
    for character in root.findall(".//character"):
        x = int(character.get("x"))
        y = int(character.get("y"))
        width = int(character.get("width"))
        height = int(character.get("height"))
        char = character.get("char")
        
        char_box = (x, y, x + width, y + height, char)
        char_boxes.append(char_box)
    
    return char_boxes

# Function to draw bounding boxes
def draw_bounding_boxes(image, char_boxes):
    draw = ImageDraw.Draw(image)
    for (x1, y1, x2, y2, char) in char_boxes:
        draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
        draw.text((x1, y1 - 10), char, fill="blue")
    return image

# Function to iterate through images and xmls in desired folder with drawing bboxes on image purpose
def draw_images_with_xmls(folder_path):
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.jpg') or f.lower().endswith('.jpeg')]
    xml_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.xml')]

    for image_file, xml_file in zip(sorted(image_files), sorted(xml_files)):
        image_path = os.path.join(folder_path, image_file)
        xml_path = os.path.join(folder_path, xml_file)
        image = Image.open(image_path)
        char_boxes = parse_xml(xml_path)
        image_with_boxes = draw_bounding_boxes(image, char_boxes)
        image_with_boxes.show()

#---------------------------------------------------------------------------------------------------

# Function to process each xml file and save it in new dir with elements: root, resolution and character
def reduce_xml_file_to_chars(filename, old_dir, new_dir):
    file_path = os.path.join(old_dir, filename)
    file_path_new = os.path.join(new_dir, filename)

    try:
        # Parse the xml file
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Create a new root element to store size and labels
        new_root = ET.Element("root")

        # Extract image size and labels
        for image in root.findall("image"):
            resolution = image.find("resolution")
            if resolution is not None:
                new_root.append(resolution)
            
            # Create new element to store all labels
            all_chars = ET.SubElement(new_root, "all_chars")

            # Find and add all labels
            words = image.find("words")
            if words is not None:
                for word in words.findall("word"):
                    for char in word.findall("character"):
                        all_chars.append(char)
        
        # Save the modified xml
        new_tree = ET.ElementTree(new_root)
        new_tree.write(file_path_new, encoding="utf-8", xml_declaration=True)

    except ET.ParseError as e:
        print(f"ParseError in file {file_path}: {e}")

#---------------------------------------------------------------------------------------------------

# Function to convert xml to yolo format used for training
def convert_xml_to_yolo(xml_path, char_to_class, image_width=640, image_height=480):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Extract image size
    resolution = root.find('resolution')
    if resolution is not None:
        img_width = int(resolution.get('x', image_width))
        img_height = int(resolution.get('y', image_height))
    
    yolo_annotations = []
    
    # Iterate through all chars
    all_chars = root.find('all_chars')
    for character in all_chars.findall('character'):
        # Extract yolo coordinates
        char = character.get('char')
        x = int(character.get('x'))
        y = int(character.get('y'))
        width = int(character.get('width'))
        height = int(character.get('height'))
        
        # Get the class id from the char_to_class mapping
        if char in char_to_class:
            class_idx = char_to_class[char]
        else:
            class_idx = -1
            #print(f"Character {char} not found in mapping!")

        if class_idx != -1:
            # Calculate center coordinates (normalized) and width/height (normalized)
            cx = (x + width / 2) / img_width
            cy = (y + height / 2) / img_height
            w = width / img_width
            h = height / img_height
            
            # Append to yolo annotations
            yolo_annotations.append(f"{class_idx} {cx} {cy} {w} {h}")
    
    return yolo_annotations

# Function to process all xml files in a folder for data conversion
def xml2yolo(input_folder, output_folder, char_to_class):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Iterate through all xml files in the input folder
    for xml_file in os.listdir(input_folder):
        if xml_file.endswith(".xml"):
            try:
                xml_path = os.path.join(input_folder, xml_file)
                yolo_annotations = convert_xml_to_yolo(xml_path, char_to_class)
                
                # Save the yolo annotations to a .txt file
                txt_filename = os.path.splitext(xml_file)[0] + ".txt"
                txt_path = os.path.join(output_folder, txt_filename)
                
                with open(txt_path, 'w') as f:
                    for annotation in yolo_annotations:
                        f.write(f"{annotation}\n")
            except:
                print(f"\n\nError in {xml_file}")

    #---------------------------------------------------------------------------------------------------