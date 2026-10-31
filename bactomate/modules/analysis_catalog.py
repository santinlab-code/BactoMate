"""Discover pipeline results without double-counting combined workbooks or figure exports."""
from pathlib import Path
import json
import os
import pandas as pd
from bactomate.modules.figure_analysis import load_tables

IGNORED={'venv','.venv','.git','__pycache__','Logs'}
EXPORTS={'source_rows.csv','plot_data.csv','figure_geometry.csv','palette.csv','replicate_summary.csv'}


def discover_results(root):
    root=Path(root).resolve()
    results=[]
    for folder,dirs,files in os.walk(root):
        dirs[:]=[d for d in dirs if d not in IGNORED and not d.startswith('figure_')]
        path=Path(folder)
        in_analysis=any(any(w in p.lower() for w in ('analys','tracking')) for p in path.relative_to(root).parts) or any(w in root.name.lower() for w in ('analys','tracking'))
        candidates=[path/name for name in sorted(files) if not name.startswith('~$') and
                    Path(name).suffix.lower() in ('.xlsx','.xlsm','.csv','.tsv') and name not in EXPORTS and
                    (in_analysis or 'analysis' in name.lower() or 'tracking' in name.lower())]
        ordinary=[p for p in candidates if not any(w in p.stem.lower() for w in ('master','combined','summary'))]
        candidates=ordinary or candidates
        # BactoMate may export both XLSX and per-cell CSV for the same sample.
        workbooks=[p for p in candidates if p.suffix in ('.xlsx','.xlsm')]
        for p in candidates:
            if p.suffix in ('.csv','.tsv') and any(p.stem==w.stem or p.stem in {w.stem.removesuffix('_analysis')+suffix for suffix in ('_per_cell','_per_cell_data','_foci','_cells')} for w in workbooks):continue
            results.append(p)
    return sorted(set(results))


def read_catalog(root,cache=None):
    root=Path(root).resolve(); entries=[]; errors=[]
    for path in discover_results(root):
        try:
            stat=path.stat(); signature=(stat.st_mtime_ns,stat.st_size)
            previous=cache.get(str(path)) if cache is not None else None
            tables=previous[1] if previous is not None and previous[0]==signature else load_tables(path)
            if cache is not None:cache[str(path)]=(signature,tables)
            for sheet,table in tables.items():
                if table.empty:continue
                low=sheet.lower().replace('-','').replace(' ','')
                columns=' '.join(str(c).lower() for c in table.columns)
                if any(w in low for w in ('runinfo','parameters','settings')):continue
                if 'summary' in low or low in ('résumé','resume','statistics'):family='Résumé · '+sheet
                elif low in ('percelldata','cells','cellmeasurements'): family='Cellules'
                elif low in ('foci','spots') or 'foci' in low:family='Foci'
                elif 'track' in low or 'track_id' in columns:family='Suivi'
                elif 'profile' in low or ('position' in columns and 'intensity' in columns):family='Profils'
                elif 'area' in columns and ('cell' in columns or 'length' in columns):family='Cellules'
                else:family='Autres · '+sheet
                identity=path.relative_to(root).as_posix()
                entries.append(dict(id=identity,path=str(path),sheet=sheet,family=family,table=table))
        except Exception as exc:errors.append(f'{path.name}: {exc}')
    return entries,errors


def read_assignments(root):
    path=Path(root)/'analysis_groups.json'
    if not path.exists():return {}
    value=json.loads(path.read_text(encoding='utf8'))
    if not isinstance(value,dict):raise ValueError('analysis_groups.json must contain a mapping.')
    return value


def save_assignments(root,assignments):
    path=Path(root)/'analysis_groups.json'; temporary=path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(assignments,ensure_ascii=False,indent=2),encoding='utf8')
    temporary.replace(path)


def assemble_catalog(entries,assignments):
    families={}
    for entry in entries:
        frame=entry['table'].copy()
        for target,aliases in [('Condition',('condition','treatment')),('Réplicat',('replicate','replicat','réplicat','biological replicate'))]:
            found=next((c for c in frame if c.lower() in aliases),None)
            if target not in frame:frame[target]=frame[found] if found else ''
        choices=assignments.get(entry['id'],{})
        for column,key in [('Condition','condition'),('Réplicat','replicate')]:
            if choices.get(key,'').strip():frame[column]=choices[key].strip()
            frame[column]=frame[column].fillna('').astype(str)
        frame['Fichier source']=entry['id'];frame['Feuille source']=entry['sheet']
        families.setdefault(entry['family'],[]).append(frame)
    priority={'Cellules':0,'Foci':1,'Suivi':2,'Profils':3}
    return {name:pd.concat(families[name],ignore_index=True,sort=False) for name in sorted(families,key=lambda n:(priority.get(n,4),n))}
