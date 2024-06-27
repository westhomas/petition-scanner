import base64
import io
import os
import re
import sys

import fitz  # PyMuPDF
import pandas as pd
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))


def log(message):
    if os.environ.get("DEBUG"):
        print(message)


def extract_images_from_pdf(pdf_path, input_filename, crop_area) -> list[tuple[str, Image.Image]]:
    doc = fitz.open(pdf_path)
    os.makedirs(input_filename, exist_ok=True)
    images = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        cropped_img = img.crop(crop_area)
        image_filename = f"page_{page_num+1}.png"
        images.append((image_filename, cropped_img))
        cropped_img.save(f"{input_filename}/{image_filename}")
    return images


def ocr_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")

    # convert image to base64 string
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please extract the text from the PNG image that is base64 encoded with utf-8. Be sure to put each field's result on the same line as the label. A label should only be one word. If you can't read the text, please say ERROR in your response and then explain more if you can.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_str}"
                        }
                    }
                ]
            },
        ]
    )
    result = response.choices[0].message.content
    if "ERROR" in result:
        raise Exception(result)
    return result


# camel case input value
def camel_case(input_value):
    return ''.join(x for x in input_value.title() if x.isalnum())


patterns = {
    "First Name": r"FIRST:?\s*(?:\n)?\s*(.+)",
    "Last Name": r"LAST:?\s*(?:\n)?\s*(.+)",
    "ZIP": r"ZIP:?\s*(?:\n)?\s*(\d+)",
    "Email": r"EMAIL:?\s*(?:\n)?\s*(\S+)",
    "Phone": r"PHONE:?\s*(?:\n)?.*?([^\n]+)"
}

def extract_data_from_text(text):
    data = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            print(f"{field}: {match.group(1)}")
            data[field] = match.group(1)
            if field == "Email":
                data[field] = data[field].strip().lower().replace(" ", "")
            elif field == "First Name" or field == "Last Name":
                data[field] = camel_case(data[field].replace(" ", "").strip())
            elif field == "Phone" or field == "ZIP":
                data[field] = re.sub(r"\D", "", data[field])
        else:
            data[field] = None
    return data


def main(pdf_path, crop_area):
    # get the input filename without the extension
    input_filename = os.path.splitext(os.path.basename(pdf_path))[0]

    output_csv = f"{input_filename}_data.csv"
    images = extract_images_from_pdf(pdf_path, input_filename, crop_area)

    data_list = []

    for image_filename, image in images:
        try:
            text = ocr_image(image)
            log(f"Extracted: {text}")
            data = extract_data_from_text(text)
            data['Image'] = image_filename
            log(f"Parsed: {data}\n\n")
            data_list.append(data)
        except Exception as e:
            print(f"{image_filename}\n============\n{e}\n\n")
            data_list.append({
                "First Name": None,
                "Last Name": None,
                "ZIP": None,
                "Email": None,
                "Phone": None,
                "Image": image_filename
            })

    df = pd.DataFrame(data_list)
    df.to_csv(output_csv, index=False)


if __name__ == "__main__":
    # read the pdf path file from the CLI arguments

    # filename = ""
    # text = ocr_image(Image.open(filename))
    # print(text)
    # data = extract_data_from_text(text)
    # print(data)
    # # print data to screen as if it was a csv line
    # print(",".join([str(x) for x in data.values()]) + "," + os.path.basename(filename))
    # sys.exit(0)


    pdf_path = sys.argv[1]

    # parse the crop area from the CLI arguments
    dims = sys.argv[2].split(",")
    if len(dims) != 4:
        print("Invalid crop area. Use format: left,top,right,bottom")
        sys.exit(1)

    left, top, right, bottom = map(int, dims)
    
    crop_area = (left, top, right, bottom)

    main(pdf_path, crop_area)
