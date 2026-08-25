from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from convert_gcj02_to_cgcs2000 import NS, convert_workbook


WORKBOOK_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''

RELATIONSHIPS_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1"
  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
  Target="/xl/worksheets/sheet1.xml"/>
</Relationships>'''

SHARED_STRINGS_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
 <si><t>lat</t></si><si><t>lng</t></si>
</sst>'''

SHEET_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
 <sheetData>
  <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
  <row r="2"><c r="A2"><v>31.830311</v></c><c r="B2"><v>121.082397</v></c></row>
 </sheetData>
</worksheet>'''


class WorkbookRelationshipRegressionTest(unittest.TestCase):
    def test_absolute_ooxml_worksheet_target_is_resolved_from_package_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.xlsx"
            destination = Path(directory) / "destination.xlsx"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("xl/workbook.xml", WORKBOOK_XML)
                archive.writestr("xl/_rels/workbook.xml.rels", RELATIONSHIPS_XML)
                archive.writestr("xl/sharedStrings.xml", SHARED_STRINGS_XML)
                archive.writestr("xl/worksheets/sheet1.xml", SHEET_XML)

            results = convert_workbook(source, destination)

            self.assertEqual(len(results), 1)
            self.assertTrue(destination.exists())
            with zipfile.ZipFile(destination) as archive:
                root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
                values = {
                    cell.get("r"): float(cell.find("x:v", NS).text)
                    for cell in root.findall("x:sheetData/x:row/x:c", NS)
                    if cell.get("r") in {"A2", "B2"}
                }
            self.assertAlmostEqual(values["A2"], 31.832086581, places=9)
            self.assertAlmostEqual(values["B2"], 121.077742102, places=9)


if __name__ == "__main__":
    unittest.main()
