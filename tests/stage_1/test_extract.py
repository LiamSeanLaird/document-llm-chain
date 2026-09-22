import xml.etree.ElementTree as ET

from app.pipeline.extract import extract_to_xml, garbage_char_frequency


def test_extract_produces_well_formed_xml(sample_pdf_path):
    xml_str = extract_to_xml(sample_pdf_path)
    root = ET.fromstring(xml_str)  # raises if not well-formed
    assert root.tag == "report"


def test_extract_captures_header_paragraph_and_table(sample_pdf_path):
    xml_str = extract_to_xml(sample_pdf_path)
    root = ET.fromstring(xml_str)

    headers = root.findall(".//header")
    paragraphs = root.findall(".//paragraph")
    tables = root.findall(".//table")

    assert any("GHG Emissions Summary" in (h.text or "") for h in headers)
    assert any("greenhouse gas emissions" in (p.text or "") for p in paragraphs)
    assert len(tables) >= 1


def test_garbage_character_frequency_below_threshold(sample_pdf_path):
    xml_str = extract_to_xml(sample_pdf_path)
    root = ET.fromstring(xml_str)
    all_text = " ".join(el.text or "" for el in root.iter() if el.text)

    assert garbage_char_frequency(all_text) < 0.02
