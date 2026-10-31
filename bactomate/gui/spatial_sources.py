"""Resolve existing project images for the figure guide; never guess across XYs."""
from pathlib import Path
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
from bactomate.modules.figure_analysis import extract_profiles


def project_spatial_sources(tab):
    from bactomate.gui.artifact_paths import (discover_mask_tiffs_for_workspace,
        infer_pipeline_dir_from_mask,resolve_filtered_foci_csv)
    from bactomate.gui.analysis_paths import resolve_analysis_workbook_for_mask,find_analysis_excel_for_mask,base_dir_for_mask
    from bactomate.gui.filter_preview_utils import short_foci_stack_label
    root=tab.context_root()
    if root is None:return []
    resolver=getattr(tab.project_window,'analyze_tab',None)
    if resolver is None:return []
    pairs=[]
    for mask in discover_mask_tiffs_for_workspace(root):
        images=resolver._resolve_fi_inputs_for_mask(mask)
        foci_images=resolver._resolve_foci_paths_for_mask(mask)
        workbook=resolve_analysis_workbook_for_mask(mask)
        if workbook is None and '_mask_filtered' in mask.stem:
            original=mask.with_name(mask.name.replace('_mask_filtered','_masks'))
            workbook=find_analysis_excel_for_mask(original,base_dir_for_mask(mask))
        source=workbook or mask
        key=source.resolve().relative_to(root).as_posix() if source.resolve().is_relative_to(root) else str(source.resolve())
        metadata={}
        for entry in tab.entries:
            if entry['id']!=key:continue
            for column,aliases,field in [('Condition',('condition','treatment'),'condition'),('Replicate',('replicate','réplicat','replicat'),'replicate')]:
                found=next((c for c in entry['table'] if c.lower() in aliases),None)
                if found:
                    values=entry['table'][found].dropna().astype(str).unique()
                    if len(values)==1:metadata[field]=values[0]
        seen=set()
        for image in images:
            image=Path(image).resolve()
            channel=short_foci_stack_label(image)
            if channel in seen:continue
            seen.add(channel)
            focus_source=next((p for p in foci_images if short_foci_stack_label(p)==channel),image)
            csv=resolve_filtered_foci_csv(infer_pipeline_dir_from_mask(mask),mask_path=mask,foci_source_path=focus_source)
            pairs.append(dict(mask=str(mask),image=str(image),channel=channel,source_id=key,
                              foci_csv=str(csv) if csv else None,
                              filtered='mask_filtered' in mask.stem,metadata=metadata))
    return pairs


class SpatialBatchWorker(QThread):
    ready=pyqtSignal(object)
    failed=pyqtSignal(str)
    progress=pyqtSignal(str)
    def __init__(self,pairs,options,assignments,parent=None):
        super().__init__(parent);self.pairs=pairs;self.options=options;self.assignments=assignments
    def run(self):
        try:
            import tifffile
            from bactomate.modules.tiff_metadata import resolve_calibration_for_mask
            tables=[];cells=[];sources=[]
            for i,pair in enumerate(self.pairs):
                self.progress.emit(f'Extracting {pair["channel"]}: {i+1}/{len(self.pairs)} XYs…')
                options=dict(self.options)
                metadata_ps,_,_,_=resolve_calibration_for_mask(Path(pair['mask']))
                if metadata_ps<=0:
                    metadata_ps,_,_,_=resolve_calibration_for_mask(Path(pair['image']))
                options['pixel_size']=metadata_ps if metadata_ps>0 else options['pixel_size']
                if not options['pixel_size'] or options['pixel_size']<=0:
                    raise ValueError(f'No pixel calibration for {Path(pair["mask"]).name}. Enter µm / px in the guide.')
                use_foci=options.pop('use_foci',False)
                if use_foci and not pair['foci_csv']:
                    raise ValueError(f'No saved filtered foci for {pair["source_id"]}. Save Filtering results first.')
                foci=pd.read_csv(pair['foci_csv']) if use_foci else None
                cell,profiles=extract_profiles(tifffile.imread(pair['mask']),tifffile.imread(pair['image']),
                    source=pair['mask'],foci=foci,**options)
                choices={**pair.get('metadata',{}),**{k:v for k,v in self.assignments.get(pair['source_id'],{}).items() if str(v).strip()}}
                for frame in (cell,profiles):
                    frame['Condition']=choices.get('condition','')
                    frame['Replicate']=choices.get('replicate','')
                    frame['Source file']=pair['source_id'];frame['channel']=pair['channel']
                tables.append(profiles);cells.append(cell)
                sources.append(dict(**pair,pixel_size=options['pixel_size'],method=options['method'],orientation=options['orientation']))
            self.ready.emit(dict(profiles=pd.concat(tables,ignore_index=True),cells=pd.concat(cells,ignore_index=True),sources=sources))
        except Exception as exc:self.failed.emit(str(exc))
