"""Independent, persistent filtering recipes for each source segmentation."""
from copy import deepcopy
from pathlib import Path
from bactomate.modules.object_curation import ObjectCuration


def source_mask(path):
    path=Path(path).resolve()
    if '_mask_filtered' in path.stem:
        folder=path.parent.parent if path.parent.name=='filtered_masks' else path.parent
        original=folder/path.name.replace('_mask_filtered','_masks')
        if original.is_file():return original
    return path


def mask_candidates(path):
    from bactomate.gui.artifact_paths import discover_mask_tiffs_for_workspace
    path=Path(path)
    root=path if path.is_dir() else path.parent
    if root.name=='filtered_masks':root=root.parent
    return sorted({source_mask(p) for p in discover_mask_tiffs_for_workspace(root)})


class MaskFilterSettings:
    def __init__(self):self.active=None;self.recipes={}
    def remember(self,path,settings):
        path=source_mask(path)
        value=deepcopy(settings)
        self.recipes[str(path)]=value
        cur=ObjectCuration(path)
        if cur.data.get('filter_settings')!=value:
            cur.data['filter_settings']=value;cur.save()
    def recipe(self,path,fallback):
        path=source_mask(path);key=str(path)
        if key not in self.recipes:
            saved=ObjectCuration(path).data.get('filter_settings')
            self.recipes[key]=deepcopy(saved if isinstance(saved,dict) else fallback)
        return deepcopy(self.recipes[key])
    def activate(self,path,current):
        path=source_mask(path)
        self.was_restored=str(path) in self.recipes or isinstance(ObjectCuration(path).data.get('filter_settings'),dict)
        if self.active is not None:self.remember(self.active,current)
        value=self.recipe(path,current);self.active=path
        return value
