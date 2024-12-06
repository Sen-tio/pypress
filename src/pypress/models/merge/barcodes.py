from abc import ABC, abstractmethod
from io import BytesIO

import qrcode
from PIL import Image
from pdflib_extended.pdflib import PDFlib
from pylibdmtx.pylibdmtx import Encoded, encode


class Barcode(ABC):
    def __init__(self, p: PDFlib, data: str):
        self.p = p
        self.data = data
        self.handle = None

    def __enter__(self) -> int:
        self.handle: int = self.create_handle()
        return self.handle

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.p.close_image(self.handle)

    def create_handle(self) -> int:
        buffer = BytesIO()

        image: Image = self.create_image()
        image.save(buffer, kind="PNG")

        pvf_path = f"/pvf/{self.data}"
        if not int(self.p.info_pvf(pvf_path, "exists")):
            self.p.create_pvf(pvf_path, buffer.getvalue(), "")

        p_image: int = self.p.load_image("png", pvf_path, "")
        if p_image < 0:
            print(self.p.get_errmsg())
            return p_image

        return p_image

    @abstractmethod
    def create_image(self) -> Image:
        pass


class Datamatrix(Barcode):
    def create_image(self) -> Image:
        data_bytes: bytes = self.data.encode()
        encoded_data: Encoded = encode(data_bytes)

        image = Image.frombytes(
            "RGB", (encoded_data.width, encoded_data.height), encoded_data.pixels
        )

        return image


class QRCode(Barcode):
    def create_image(self) -> Image:
        qr = qrcode.main.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=0,
        )

        qr.add_data(self.data)
        qr.make()

        image = qr.make_image(fill_color="black", back_color="white")

        return image


class BarcodeFactory:
    def __init__(self, p: PDFlib):
        self.p = p

    def create_barcode(self, data: str, barcode_type: str) -> Barcode:
        barcode_type: str = barcode_type.casefold()

        if barcode_type == "datamatrix":
            return Datamatrix(self.p, data)
        elif barcode_type == "qr_code":
            return QRCode(self.p, data)
        else:
            raise ValueError(f"Unsupported barcode type: {barcode_type}")
