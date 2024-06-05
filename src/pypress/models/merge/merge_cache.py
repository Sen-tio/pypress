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


@dataclass
class Page:
    handle: int
    image_handle: int
    number: int
    width: float
    height: float
    blocks: list[Block] = field(default_factory=list)


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

    def clear_cache(self) -> None:
        if not self._cached_documents:
            return

        for image_handle in self._cached_images.values():
            self.p.close_image(image_handle)

        for doc in self._cached_documents.values():
            for page in doc.pages:
                self.p.close_image(page.image_handle)
                self.p.close_pdi_page(page.handle)
            self.p.close_pdi_document(doc.handle)

        self._cached_documents.clear()

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

        return Block(block_name, block_type, block_text, block_page)
