import pandas as pd
from bactomate.modules.output_audit import audit_outputs


def test_readonly_audit_distinguishes_stage_copies_and_optional_table_exports(tmp_path):
    folder=tmp_path/'_analysis';folder.mkdir()
    table=pd.DataFrame({'cell_id':[1,2],'area_um2':[1.2,2.3]})
    book=folder/'sample_analysis.xlsx'
    with pd.ExcelWriter(book) as writer:table.to_excel(writer,sheet_name='Per-Cell Data',index=False)
    csv=folder/'sample_analysis_per_cell.csv';table.to_csv(csv,index=False)
    copy=folder/'legacy_copy.csv';copy.write_bytes(csv.read_bytes())
    original=tmp_path/'original_image.tif';original.write_bytes(b'keep source')
    before={p:p.read_bytes() for p in [book,csv,copy,original]}
    report=audit_outputs(tmp_path)
    rows={row['path']:row for row in report['files']}
    assert len(rows)==3 and 'original_image.tif' not in rows
    assert rows['_analysis/sample_analysis.xlsx']['same_table']
    assert rows['_analysis/legacy_copy.csv']['same_content']==['_analysis/sample_analysis_per_cell.csv']
    assert all(path.read_bytes()==data for path,data in before.items())
