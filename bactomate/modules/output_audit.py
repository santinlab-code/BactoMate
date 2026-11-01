"""Read-only inspection of generated artifacts; never removes stage outputs."""
from pathlib import Path
import hashlib
from collections import defaultdict


def role(path):
    name=path.name.lower()
    if any(part.startswith('figure_') for part in path.parts[:-1]):return 'Figure export / reproducibility bundle'
    if '_mask_filtered' in name:return 'Filtered cells' if path.suffix.lower() in ('.tif','.tiff') else 'Filter settings / provenance'
    if 'foci_filtered' in name:return 'Filtered foci'
    if '_masks' in name and path.suffix.lower() in ('.tif','.tiff'):return 'Source segmentation / tracked masks'
    if path.suffix.lower()=='.png':return 'Single-frame preview of a TIFF' if path.with_suffix('.tif').is_file() or path.with_suffix('.tiff').is_file() else 'PNG image / figure'
    if path.suffix.lower() in ('.pdf','.svg'):return 'Exported figure'
    if path.suffix.lower()=='.json':return 'Settings / manual curation / provenance'
    if path.suffix.lower() in ('.xlsx','.csv','.tsv'):return 'Measurements / tracking table'
    return 'Image / quality-control output'


def audit_outputs(root,progress=None):
    root=Path(root).resolve();rows=[];groups=defaultdict(list);issues=[]
    import os
    files=[]
    for folder,dirs,names in os.walk(root):
        dirs[:]=[name for name in dirs if name not in ('venv','.venv','.git','__pycache__','Logs')]
        directory=Path(folder)
        if any(part.startswith(('_segmentation','_analysis','_tracking')) for part in directory.relative_to(root).parts) or root.name.startswith(('_segmentation','_analysis','_tracking')):
            files.extend(directory/name for name in names)
    files.sort()
    for i,path in enumerate(files):
        if progress:progress(f'Inspecting generated files: {i+1}/{len(files)}')
        try:
            size=path.stat().st_size
            row=dict(path=str(path.relative_to(root)),role=role(path),size_bytes=size,same_content=[],same_table=[])
            if size:
                with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
                groups[(size,digest)].append(row)
            rows.append(row)
        except OSError as exc:issues.append(f'{path.name}: {exc}')
    for group in groups.values():
        if len(group)>1:
            for row in group:row['same_content']=[other['path'] for other in group if other is not row]
    by_path={row['path']:row for row in rows}
    # Optional analysis CSVs can repeat workbook sheets even if their file bytes differ.
    for row in rows:
        book=root/row['path']
        if book.suffix.lower()!='.xlsx':continue
        for suffix,sheet in [('_summary.csv','Summary'),('_per_cell.csv','Per-Cell Data'),('_foci.csv','Foci')]:
            csv=book.with_name(book.stem+suffix)
            key=str(csv.relative_to(root))
            if key not in by_path:continue
            try:
                import pandas as pd
                left=pd.read_excel(book,sheet_name=sheet);right=pd.read_csv(csv)
                pd.testing.assert_frame_equal(left,right,check_dtype=False,check_exact=True)
                row['same_table'].append(f'{key} ({sheet})');by_path[key]['same_table'].append(f'{row["path"]} → {sheet}')
            except AssertionError:pass
            except Exception as exc:issues.append(f'Cannot compare {csv.name}: {exc}')
    return dict(root=str(root),files=rows,issues=issues,
        notes=['Source and filtered masks/foci are separate pipeline stages, even if identical after a no-op filter.',
               'PNG previews and TIFF stacks have different purposes; PNG contains one frame.',
               'Analysis CSVs are optional copies of workbook sheets (Also save CSV is off by default).',
               'Combined/master workbooks aggregate samples and intentionally overlap individual results.',
               'No files were changed or deleted.'])
