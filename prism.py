#!/usr/bin/python3

from PIL import Image, ImageOps
import math
import gzip
import argparse
import os

parser = argparse.ArgumentParser(description="I don't know, I just wrote it",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-v", "--verbose", action="store_true", help="increase verbosity")
parser.add_argument("-vv", "--vverbose", action="store_true", help="increase verbosity a lot")
parser.add_argument("-s", "--silent", action="store_true", help="decrease verbosity")
parser.add_argument("file", help="Exfiltrated image file")
parser.add_argument("-o", "--outfile", help="Filename to save the extracted data to")

args = parser.parse_args()
config = vars(args)

verbose = 0 if config['silent'] else 2 if config['verbose'] else 3 if config['vverbose'] else 1

background_pixel = (0, 0, 0)
sample_percent = 0.2
contention_tolerance = 0.45
border_tolerance = 0.05
color_tolerance = 20

# Powershell Colors
color_keys = {(0,0,0):0x0,
              (0,7,17):0x0,
              (0,0,139):0x1,
              (0,7,128):0x1,
              (0,100,0):0x2,
              (0,87,17):0x2,
              (0,139,139):0x3,
              (0,118,128):0x3,
              (139,0,0):0x4,
              (111,7,17):0x4,
              (139,0,139):0x5,
              (111,7,128):0x5,
              (170,170,0):0x6,
              (136,143,17):0x6,
              (169,169,169):0x7,
              (135,142,152):0x7,
              (128,128,128):0x8,
              (102,109,119):0x8,
              (0,0,255):0x9,
              (0,7,221):0x9,
              (0,255,0):0xa,
              (0,211,7):0xa,
              (0,255,255):0xb,
              (0,211,221):0xb,
              (255,0,0):0xc,
              (204,7,17):0xc,
              (255,0,255):0xd,
              (204,7,221):0xd,
              (255,255,0):0xe,
              (204,211,17):0xe,
              (255,255,255):0xf,
              (204,211,221):0xf}

# Pretty Terminal Things
RED = "\033[0;31m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
YELLOW = "\033[1;33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def splash():
    print(f"{RED}██████  ██████  ██ ███████ ███    ███")
    print(f"{YELLOW}██   ██ ██   ██ ██ ██      ████  ████")
    print(f"{GREEN}██████  ██████  ██ ███████ ██ ████ ██")
    print(f"{CYAN}██      ██   ██ ██      ██ ██  ██  ██")
    print(f"{RESET}██      ██   ██ ██ ███████ ██      ██")
    print("PowerShell Raster Image Salvage Module")
    print("")
    print("\"I just wanted a cool sounding name for this.\"")
    print("    - TheMiggiestMig")
    print("")
    print(f"#######################################")



def process_image(file):
    info(f"Processing image '{file}'...")
    image = Image.open(file, 'r')
    success(f"Loaded image '{file}'")
    debug(f"image:{{width:{image.width}, height:{image.height}, size:{len(image.tobytes())}}}")
    
    find_image_bounds(image)



def find_image_bounds(image):
    global background_pixel

    info(f"(Pass 1/3) Identifying work space...")

    # Sample some border pixels to determine the background color.
    samples = {}
    coords = [(0, 0), (image.width, 0), (0, image.height), (image.width, image.height)]

    for pt in coords:
        pixel = image.getpixel((0,0))
        samples[pixel] = samples[pixel] + 1 if pixel in samples.keys() else 1
    
    num_distinct = len(samples.keys())
    debug(f"{num_distinct} distict background pixel value{'s' if num_distinct > 1 else ''} found")

    if num_distinct > 1:
        warn("More than 1 distinct sample value found")
        warn("Ensure you crop part of the empty space around the image")
        error("Cannot find bounding box")
        exit()

    background_pixel = pixel
    success("\tBackground pixel selected", level=2)
    
    # Create a new image with a black background to bind the bounding box.
    info("\tCropping image to bounding box")
    data = image.getdata()
    new_data = []
    for pt in data:
        if pt == pixel:
            new_data.append((0,0,0))
        else:
            new_data.append(pt)

    new_image = Image.new(mode="RGB", size=(image.width, image.height))
    new_image.putdata(new_data)
    new_image = image.crop(new_image.getbbox())
    success("\tWorkspace defined")

    refine_blocks(new_image)



def refine_blocks(image):
    info("(Pass 2/3) Defining blocks and extracting values...")
    block_map = map_blocks(image)
    extracted_values = []
    contentions = 0

    block_count = 0
    total_blocks = len(block_map['rows']) * len(block_map['columns'])

    r_start = 0
    for r, row in enumerate(block_map['rows']):
        r_end = block_map['rows'][r] if r < len(block_map['rows']) else image.height

        c_start = 0
        for c, column in enumerate(block_map['columns']):
            block_count += 1
            c_end = block_map['columns'][c] if c < len(block_map['columns']) else image.width
            block_values = {}

            pad = os.get_terminal_size().columns
            print(f"\r{' '*pad}\r",end="")

            if block_count + 1 < total_blocks:
                info(f"\tScanning block {block_count}/{total_blocks} ({round((block_count / total_blocks) * 100, 2)}%)...\r",end="")

            # Count the different pixels in this block
            for y in range(r_start+1, r_end):
                for x in range(c_start+1, c_end):
                    pixel = image.getpixel((x,y))

                    # Skip if this is a background color pixel
                    if pixel == background_pixel:
                        continue

                    # Find the color_key with the closest match
                    key_pixel = None
                    key_pixel_distance = 0xFFFFFF

                    for key in color_keys:
                        distance = math.dist(pixel, key)

                        if distance < key_pixel_distance or distance < color_tolerance:
                            key_pixel = key
                            key_pixel_distance = distance

                    block_values[color_keys[key_pixel]] = block_values[color_keys[key_pixel]] + 1 if color_keys[key_pixel] in block_values.keys() else 1
            
            '''
            # DEBUG - Show Grid
            for y in range(r_start, r_end):
                image.putpixel((c_start, y), (255,255,0))

            for x in range(c_start, c_end):
                image.putpixel((x, r_start), (255,255,0))
            '''

            # Determine if there is a clear winner
            block_values = sorted(block_values.items(), key=lambda x:x[1], reverse=True)

            if len(block_values) > 1:
                ratio = block_values[1][1] / block_values[0][1]

                if ratio > contention_tolerance:
                    contentions += 1
                    warn(f"\nContention found in BLOCK {(r,c)} [{round(ratio * 100,2)}%]: ({block_values[0][0]}){block_values[0][1]} vs ({block_values[1][0]}){block_values[1][1]}",level=2)
                    
                    for y in range(r_start, r_end):
                        image.putpixel((c_start, y), (255,0,0))
                        image.putpixel((c_end, y), (255,0,0))

                    for x in range(c_start, c_end):
                        image.putpixel((x, r_start), (255,0,0))
                        image.putpixel((x, r_end), (255,0,0))
            
            # Background blocks don't get values assigned. Only add the block if it has a value.
            if len(block_values):
                extracted_values.append(block_values[0][0])
            else:
                debug(f"No value assigned for {(c,r)}")

            c_start = column

        r_start = row
    success(f"\tScan completed {block_count}/{total_blocks} (100%)")
    info("\tChecking for contentions")
    if contentions:
        warn(f"\t{contentions} block contentions were found.")
        warn(f"\tThere is uncertainty (> {int(contention_tolerance*100)}%) for one or more block values, which may result in failure.")
    else:
        success("\tNo contentions found")

    if len(extracted_values) % 2:
        warn("\tAn odd number of values were extracted (possibly due to pixel bleed into the last block)")
        warn("\tRemoving the last block and attempting again")
        extracted_values = extracted_values[:-1]

    success(f"\tExtracted {len(extracted_values)} values ({len(extracted_values)//2} bytes)")
    retrieve_data(extracted_values)



def retrieve_data(data_values):
    info("(Pass 3/3) Retrieving data from extracted values...")

    # Pair the values into their original byte values
    assembled_values = []

    for i in range(0, len(data_values), 2):
        assembled_values.append(int(hex(data_values[i]) + hex(data_values[i + 1])[2:], 16))

    info("\tAttempting to decompress assembled archive")
    # Attempt to decompress the gzip
    try:
        data = gzip.decompress(bytes(assembled_values))
    except Exception as e:
        error(f"An error occured during decompression: {{{e}}}")
        exit()
    success("\tData decompressed")

    # Write the data to file
    outfile = config['outfile'] if config['outfile'] else config['file']+".out"
    info("\tWriting to file")

    with open(outfile, 'wb') as file:
        file.write(data)

    success(f"\tSuccessfully written data to '{outfile}' ({len(data)} bytes)")



# The blocks possibly aren't the same size, so try to map their boundaries.
def map_blocks(image):
    gs = ImageOps.grayscale(image)

    # Mark contiguous pixel zones and vote on the most likely bounds [columns].
    col_map = [0 for i in range(gs.width)]

    for y in range(int(gs.height * sample_percent)):
        contiguous_step = 0
        previous_pixel = None

        for x in range(gs.width):
            pixel = gs.getpixel((x,int(y / sample_percent)))

            if pixel == previous_pixel or pixel == background_pixel:
                contiguous_step += 1
            else:
                if contiguous_step:
                    #gs.putpixel((x,y), 255)
                    col_map[x] += 1

                contiguous_step = 0

            previous_pixel = pixel

        col_map[-1] += 1

    x_bounds = []

    # Check the votes of neighboring columns, and declare a border when a winner is found.
    for x, val in enumerate(col_map):
        pre = col_map[x-1] if x > 0 else 0
        post = col_map[x+1] if x+1 < len(col_map) else 0

        if val > pre and val >= post and val > border_tolerance * gs.height:
            success(f"New boundary marked at x:{x}", level=3)
            x_bounds.append(x)
            debug(f"Defined by {pre} [{val}] {post}")
        else:
            debug(f"Skipping... {pre} [{val}] {post}")

    for y in range(gs.height):
        for x in x_bounds:
            gs.putpixel((x, y), 255)

    # Mark contiguous pixel zones and vote on the most likely bounds [rows].
    row_map = [0 for i in range(gs.height)]

    for x in range(int(gs.width * sample_percent)):
        contiguous_step = 0
        previous_pixel = None

        for y in range(gs.height):
            pixel = gs.getpixel((int(x / sample_percent),y))

            if pixel == previous_pixel or pixel == background_pixel:
                contiguous_step += 1
            else:
                if contiguous_step:
                    #gs.putpixel((x,y), 255)
                    row_map[y] += 1

                contiguous_step = 0

            previous_pixel = pixel

        row_map[-1] += 1

    y_bounds = []

    # Check the votes of neighboring rows, and declare a border when a winner is found.
    for y, val in enumerate(row_map):
        pre = row_map[y-1] if y > 0 else 0
        post = row_map[y+1] if y+1 < len(row_map) else 0

        if val > pre and val >= post and val > border_tolerance * gs.width:
            success(f"\tNew boundary marked at y:{y}", level=3)
            y_bounds.append(y)
            debug(f"\tDefined by {pre} [{val}] {post}")
        else:
            debug(f"\tSkipping... {pre} [{val}] {post}")

    for x in range(gs.width):
        for y in y_bounds:
            gs.putpixel((x, y), 255)

    success(f"\tBlock borders defined [{len(y_bounds)} rows, {len(x_bounds)} columns]")

    return {'rows':y_bounds, 'columns':x_bounds}



def log(msg, level=0, end='\n'):
    if verbose >= level: print(msg, end=end)



def debug(msg, level=3, end='\n'):
    log(f"{CYAN}[DEBUG] {msg}{RESET}", level, end)



def info(msg,level=1, end='\n'):
    log(f"{CYAN}{BOLD}[*]{RESET} {msg}", level, end)



def success(msg, level=1, end='\n'):
    log(f"{GREEN}{BOLD}[+]{RESET} {msg}", level, end)



def warn(msg, level=1, end='\n'):
    log(f"{YELLOW}{BOLD}[-]{RESET}{YELLOW} {msg}{RESET}", level, end)



def error(msg, level=1, end='\n'):
    log(f"{RED}{BOLD}[!] {msg}{RESET}", level, end)



if __name__ ==  "__main__":
    if not config['silent']: splash()
    process_image(config['file'])