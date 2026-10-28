from pathlib import Path


def pdf_part(name: str, data: bytes):
    return ("files", (name, data, "application/pdf"))


async def test_upload_and_list(client, make_pdf):
    p = make_pdf(["hello world"])
    r = await client.post("/api/documents", files=[pdf_part("doc.pdf", p.read_bytes())])
    body = r.json()
    assert r.status_code == 200
    assert body["results"] == [{"filename": "doc.pdf", "pages": 1, "chunks": 1}]
    assert body["errors"] == []
    assert (await client.get("/api/documents")).json() == [{"filename": "doc.pdf", "chunks": 1}]


async def test_non_pdf_only_is_400(client):
    r = await client.post("/api/documents", files=[("files", ("notes.txt", b"hi", "text/plain"))])
    assert r.status_code == 400


async def test_corrupt_pdf_reported_others_ingested(client, make_pdf):  # Review Focus 2
    good = make_pdf(["fine"])
    r = await client.post(
        "/api/documents",
        files=[pdf_part("bad.pdf", b"not a pdf at all"), pdf_part("good.pdf", good.read_bytes())],
    )
    body = r.json()
    assert r.status_code == 200
    assert [e["filename"] for e in body["errors"]] == ["bad.pdf"]
    assert [x["filename"] for x in body["results"]] == ["good.pdf"]


async def test_blank_pdf_reported(client, make_pdf):
    r = await client.post(
        "/api/documents", files=[pdf_part("blank.pdf", make_pdf([""]).read_bytes())]
    )
    assert r.json()["errors"] == [{"filename": "blank.pdf", "detail": "No extractable text"}]


async def test_oversized_file_rejected(client, make_pdf, settings):  # Review Focus 1
    big = b"%PDF-1.4\n" + b"0" * (settings.max_upload_mb * 1024 * 1024)
    good = make_pdf(["fine"])
    r = await client.post(
        "/api/documents", files=[pdf_part("big.pdf", big), pdf_part("good.pdf", good.read_bytes())]
    )
    assert r.json()["errors"] == [{"filename": "big.pdf", "detail": "File exceeds 10 MB limit"}]
    assert [x["filename"] for x in r.json()["results"]] == ["good.pdf"]
    assert not (Path(settings.upload_dir) / "big.pdf").exists()


async def test_filename_sanitized_and_case_insensitive(client, make_pdf, settings):  # Focus 3
    p = make_pdf(["x"])
    r = await client.post(
        "/api/documents", files=[pdf_part("../../Q3 Report ü.PDF", p.read_bytes())]
    )
    assert r.json()["results"][0]["filename"] == "Q3 Report ü.PDF"
    assert (Path(settings.upload_dir) / "Q3 Report ü.PDF").exists()
    assert not (Path(settings.upload_dir).parent.parent / "Q3 Report ü.PDF").exists()


async def test_windows_style_path_sanitized(client, make_pdf, settings):
    p = make_pdf(["x"])
    r = await client.post("/api/documents", files=[pdf_part(r"C:\Users\me\a.pdf", p.read_bytes())])
    assert r.json()["results"][0]["filename"] == "a.pdf"
    assert sorted(f.name for f in Path(settings.upload_dir).iterdir()) == ["a.pdf"]
