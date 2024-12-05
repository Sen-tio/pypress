import qrcode
from abc import ABC, abstractmethod
from io import BytesIO

from PIL import Image
from pdflib_extended.pdflib import PDFlib
from pylibdmtx.pylibdmtx import Encoded, encode


class Barcode(ABC):
    def __init__(self, p: PDFlib, data: str):
        self.p = p
        self.data = data
        self.handle = None

    def __enter__(self) -> int:
        buffer: BytesIO = self.create_image()
        self.handle: int = self.load_handle_from_buffer(buffer)
        return self.handle

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.p.close_image(self.handle)

    def load_handle_from_buffer(self, buffer: BytesIO) -> int:
        pvf_path = f"/pvf/{self.data}"
        if not int(self.p.info_pvf(pvf_path, "exists")):
            self.p.create_pvf(pvf_path, buffer.getvalue(), "")

        p_image: int = self.p.load_image("png", pvf_path, "")
        if p_image < 0:
            print(self.p.get_errmsg())
            return p_image

        return p_image

    @abstractmethod
    def create_image(self) -> BytesIO:
        pass


class Datamatrix(Barcode):
    def create_image(self) -> BytesIO:
        data_bytes: bytes = self.data.encode()
        encoded_data: Encoded = encode(data_bytes)

        image = Image.frombytes(
            "RGB", (encoded_data.width, encoded_data.height), encoded_data.pixels
        )

        buffer = BytesIO()
        image.save(buffer, format="PNG")

        return buffer


class QRCode(Barcode):
    def create_image(self) -> BytesIO:
        qr = qrcode.main.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=0,
        )

        qr.add_data(self.data)
        qr.make()

        image = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        image.save(buffer, kind="PNG")

        return buffer
