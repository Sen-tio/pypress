from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from pdflib_extended.pdflib import PDFlib


class MergeCacheException(Exception):
    pass


@dataclass
class Block:
    name: str
    type: str
    text: str
    page: int = None
    custom_properties: dict[str, Union[str, int, float]] = None


@dataclass
class Page:
    handle: int
    image_handle: int
    number: int
    width: float
    height: float
    blocks: list[Block] = field(default_factory=list)
    is_block_reference: bool = False


@dataclass
class Document:
    name: str
    handle: int
    pages: list[Page] = field(default_factory=list)


class MergeCache:
    def __init__(self, p: PDFlib) -> None:
        self.p = p
        self._cached_documents: dict[str, Document] = {}
        self._cached_images: dict[str, int] = {}
        self._cached_graphics: dict[str, int] = {}

    def get_or_cache_document(self, file_path: Union[str, Path]) -> Document:
        file_path = Path(file_path)

        if file_path.as_posix() in self._cached_documents.keys():
            return self._cached_documents[file_path.as_posix()]

        doc: Document = self._load_document(file_path)
        self._cached_documents[file_path.as_posix()] = doc
        return doc

    def get_or_cache_image(self, file_path: Union[str, Path]) -> int:
        image_path = Path(file_path)

        if not image_path.exists():
            raise MergeCacheException(f"Image does not exist: {file_path}")

        if image_path.as_posix() in self._cached_images.keys():
            return self._cached_images[image_path.as_posix()]

        image_handle = self._load_image(image_path)
        self._cached_images[image_path.as_posix()] = image_handle
        return image_handle

    def get_or_cache_graphics(self, file_path: Union[str, Path]) -> int:
        graphics_path = Path(file_path)

        if not graphics_path.exists():
            raise MergeCacheException(f"Graphics does not exist: {file_path}")

        if graphics_path.as_posix() in self._cached_graphics.keys():
            return self._cached_graphics[graphics_path.as_posix()]

        graphics_handle: int = self._load_graphics(graphics_path)
        self._cached_graphics[graphics_path.as_posix()] = graphics_handle
        return graphics_handle

    def get_or_cache_pdf_page(
        self, file_path: Union[str, Path], page_number: int
    ) -> Page:
        doc = None
        file_path = Path(file_path)

        if file_path.as_posix() in self._cached_documents.keys():
            doc: Document = self._cached_documents[file_path.as_posix()]
            for page in doc.pages:
                if page.number == page_number:
                    return page

        if doc is None:
            doc_handle: int = self.p.open_pdi_document(file_path.as_posix(), "")
            if doc_handle < 0:
                raise MergeCacheException(self.p.get_errmsg())
            doc = Document(file_path.as_posix(), doc_handle)

        page_handle: int = self.p.open_pdi_page(doc.handle, page_number, "")
        if page_handle < 0:
            raise MergeCacheException(self.p.get_errmsg())

        pdf_block_page = Page(
            page_handle, -1, page_number, 0, 0, is_block_reference=True
        )
        doc.pages.append(pdf_block_page)

        self._cached_documents[file_path.as_posix()] = doc
        return pdf_block_page

    def clear_cache(self) -> None:
        if not self._cached_documents:
            return

        for image_handle in self._cached_images.values():
            self.p.close_image(image_handle)

        for doc in self._cached_documents.values():
            for page in doc.pages:
                if not page.is_block_reference:
                    self.p.close_image(page.image_handle)
                self.p.close_pdi_page(page.handle)
            self.p.close_pdi_document(doc.handle)

        self._cached_documents.clear()

    def _load_graphics(self, file_path: Path) -> int:
        graphics_handle: int = self.p.load_graphics("auto", file_path.as_posix(), "")
        if graphics_handle < 0:
            raise MergeCacheException(self.p.get_errmsg())
        return graphics_handle

    def _load_image(self, file_path: Path) -> int:
        image_handle: int = self.p.load_image("auto", file_path.as_posix(), "")
        if image_handle < 0:
            raise MergeCacheException(self.p.get_errmsg())
        return image_handle

    def _load_document(self, file_path: Path) -> Document:
        doc_handle: int = self.p.open_pdi_document(file_path.as_posix(), "")
        if doc_handle < 0:
            raise MergeCacheException(self.p.get_errmsg())

        doc = Document(name=file_path.as_posix(), handle=doc_handle)
        page_count = int(self.p.pcos_get_number(doc_handle, "length:pages"))

        for page in range(page_count):
            doc.pages.append(self._load_page(doc, page))

        return doc

    def _load_page(self, doc: Document, page_index: int) -> Page:
        page_handle: int = self.p.open_pdi_page(doc.handle, page_index + 1, "")
        if page_handle < 0:
            raise MergeCacheException(self.p.get_errmsg())

        width: float = self.p.pcos_get_number(doc.handle, f"pages[{page_index}]/width")
        height: float = self.p.pcos_get_number(
            doc.handle, f"pages[{page_index}]/height"
        )

        image_handle: int = self.p.begin_template_ext(width, height, "")
        if image_handle < 0:
            raise MergeCacheException(self.p.get_errmsg())

        self.p.fit_pdi_page(page_handle, 0, 0, "")
        self.p.end_template_ext(
            0,
            0,
        )

        page = Page(page_handle, image_handle, page_index + 1, width, height)
        block_count = int(
            self.p.pcos_get_number(doc.handle, f"length:pages[{page_index}]/blocks")
        )

        for i in range(block_count):
            page.blocks.append(self._load_block(doc, page, i))

        return page

    def _load_block(self, doc: Document, page: Page, block_index: int) -> Block:
        block_path = f"pages[{page.number - 1}]/blocks[{block_index}]"

        block_page = None
        block_name = self.p.pcos_get_string(doc.handle, f"{block_path}.key")
        block_type = self.p.pcos_get_string(doc.handle, f"{block_path}/Subtype")
        block_text = self.p.pcos_get_string(
            doc.handle, f"{block_path}/default{block_type.lower()}"
        )

        if block_type.lower() == "pdf":
            if (
                self.p.pcos_get_string(doc.handle, f"{block_path}.val[8].key")
                == "defaultpdfpage"
            ):
                block_page = int(
                    self.p.pcos_get_number(doc.handle, f"{block_path}.val[8]")
                )
            else:
                block_page = 1

        # Get any custom properties associated with the block
        custom_properties: dict[str, Union[str, int, float]] = {}
        custom_property_count = int(
            self.p.pcos_get_number(doc.handle, f"length:{block_path}/Custom")
        )

        for i in range(custom_property_count):
            key = self.p.pcos_get_string(doc.handle, f"{block_path}/Custom[{i}].key")
            val = self.p.pcos_get_string(doc.handle, f"{block_path}/Custom[{i}].val")
            custom_properties[key] = val

        return Block(block_name, block_type, block_text, block_page, custom_properties)
