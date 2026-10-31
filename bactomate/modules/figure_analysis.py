"""Table-driven figures and explicit principal-axis fluorescence profiles.

No implicit tracking, missing-pixel filling, or fluorescence normalization.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd

KINDS = ('Histogram', 'Scatter', 'Mean curve', 'Box plot', 'Violin plot', 'ECDF',
         'Correlation', 'Demograph', 'Kymograph', 'Normalized cell heatmap', 'Heatmap', 'Maxima map', 'Foci count')


@dataclass
class FigureSpec:
    kind: str = 'Histogram'
    x: str = ''
    y: str = ''
    value: str = ''
    group: str = ''
    sort: str = ''
    bins: int = 40
    title: str = ''
    cmap: str = 'viridis'
    filter_column: str = ''
    filter_value: str = ''
    minimum: float | None = None
    maximum: float | None = None
    track_confirmed: bool = False
    normalization: str = 'raw'
    replicate: str = ''
    show_replicates: bool = True
    relative_position: bool = False
    maxima_profile: str = 'maximum'
    show_points: bool = True
    density_bins: int = 96
    density_sigma: float = 2.0


def load_tables(path):
    path = Path(path)
    if path.suffix.lower() in ('.xlsx', '.xlsm'):
        tables = pd.read_excel(path, sheet_name=None)
    else:
        tables = {path.stem: pd.read_csv(path, sep='\t' if path.suffix.lower() == '.tsv' else ',')}
    result = {}
    for key, table in tables.items():
        table.columns = table.columns.map(str)
        if table.columns.duplicated().any():
            raise ValueError('Duplicate column names are not supported.')
        result[str(key)] = table
    return result


def extract_profiles(masks, images, *, pixel_size, source, bins=48, across=16,
                     orientation='geometric', method='principal axis', foci=None):
    """Pixel skeleton or straight principal-axis profiles (not MicrobeJ subpixel contours).

    Pixels are averaged in normalized bins; empty bins remain NaN. Polarity is
    geometric unless explicit bright-pole alignment is selected. Labels are local
    to each frame, never assumed to be tracks.
    """
    from skimage.measure import regionprops
    masks, images = np.asarray(masks), np.asarray(images)
    if masks.ndim == 2: masks = masks[None]
    if images.ndim == 2: images = images[None]
    if masks.ndim != 3 or masks.shape != images.shape:
        raise ValueError('Choose matching TYX label masks and one fluorescence channel, with identical dimensions.')
    if not np.issubdtype(masks.dtype, np.integer) or (masks < 0).any():
        raise ValueError('Masks must contain non-negative integer cell labels.')
    if not np.isfinite(pixel_size) or pixel_size <= 0:
        raise ValueError('Enter a valid pixel calibration in µm / px.')
    if orientation not in ('geometric', 'bright pole'):
        raise ValueError('Unknown orientation.')
    cells, samples = [], []
    foci = pd.DataFrame(foci).copy() if foci is not None else None
    if foci is not None and not foci.empty:
        if not {'x','y'}.issubset(foci):raise ValueError('Foci data needs x and y pixel coordinates.')
        if 'frame' not in foci:foci['frame']=0
        for column in ('frame','x','y'):foci[column]=pd.to_numeric(foci[column],errors='coerce')
        foci=foci.dropna(subset=['frame','x','y'])
        foci=foci[foci.frame.between(0,len(masks)-1)&foci.x.between(0,masks.shape[2]-1)&foci.y.between(0,masks.shape[1]-1)]
        foci=foci[foci.frame.eq(foci.frame.round())]
        foci['_mask_label']=masks[foci.frame.astype(int),foci.y.round().astype(int),foci.x.round().astype(int)]
    for frame, mask in enumerate(masks):
        for r in regionprops(mask):
            coords = r.coords.astype(float)
            if len(coords) < 3: continue
            centered = coords - coords.mean(axis=0)
            _, vectors = np.linalg.eigh(centered.T @ centered)
            axis = vectors[:, -1]
            if axis[np.argmax(np.abs(axis))] < 0: axis = -axis
            if method == 'medial axis':
                from skimage.morphology import skeletonize
                from scipy.ndimage import distance_transform_edt
                from scipy.spatial import cKDTree
                from scipy.sparse import csr_matrix
                from scipy.sparse.csgraph import dijkstra
                local = r.image
                center = np.argwhere(skeletonize(local))
                lookup = {tuple(p):i for i,p in enumerate(center)}
                edges, destinations, weights = [], [], []
                for i,p in enumerate(center):
                    for dy in (-1,0,1):
                        for dx in (-1,0,1):
                            if dy==dx==0:continue
                            j=lookup.get((p[0]+dy,p[1]+dx))
                            if j is not None:
                                edges.append(i); destinations.append(j); weights.append(np.hypot(dy,dx))
                graph=csr_matrix((weights,(edges,destinations)),shape=(len(center),len(center)))
                endpoints=np.flatnonzero(np.diff(graph.indptr)==1)
                if len(endpoints)!=2:
                    raise ValueError(f'Frame {frame}, cell {r.label}: medial axis is branched, cyclic or too short. Curate the mask or choose principal axis.')
                distances,previous=dijkstra(graph,indices=int(endpoints[0]),return_predecessors=True)
                chain=[int(endpoints[1])]
                while chain[-1]!=endpoints[0]:
                    nxt=int(previous[chain[-1]])
                    if nxt<0:raise ValueError('Disconnected medial axis.')
                    chain.append(nxt)
                center=center[chain]
                # Deterministic geometric direction; no pole-age inference.
                if (center[-1]-center[0]) @ axis < 0:center=center[::-1]
                distances=np.r_[0,np.cumsum(np.linalg.norm(np.diff(center,axis=0),axis=1))]
                local_coords=coords-np.array(r.bbox[:2])
                _,nearest=cKDTree(center).query(local_coords)
                u=2*distances[nearest]/max(distances[-1],1e-12)-1
                tangent=np.gradient(center.astype(float),axis=0)
                tangent/=np.maximum(np.linalg.norm(tangent,axis=1)[:,None],1e-12)
                normal=np.c_[-tangent[:,1],tangent[:,0]]
                radius=distance_transform_edt(local)[tuple(center.T)]
                v=np.sum((local_coords-center[nearest])*normal[nearest],axis=1)/np.maximum(radius[nearest],1)
                v=np.clip(v,-1,1)
            elif method == 'principal axis':
                u = centered @ axis
                v = centered @ np.array([-axis[1], axis[0]])
                u = 2*(u-u.min())/max(np.ptp(u), 1e-12)-1
                v = 2*(v-v.min())/max(np.ptp(v), 1e-12)-1
            else:raise ValueError('Unknown profile coordinate method.')
            intensity = images[frame][tuple(r.coords.T)].astype(float)
            if orientation == 'bright pole':
                left, right = intensity[u < -.5], intensity[u > .5]
                if left.size and right.size and np.nanmean(right) > np.nanmean(left):
                    u, v = -u, -v
            object_key = f'{source}::frame={frame}::cell={r.label}'
            base = dict(source=source, profile_method=method, frame=frame, cell_id=int(r.label), object_key=object_key,
                        area_um2=r.area*pixel_size**2, length_um=r.major_axis_length*pixel_size,
                        width_um=r.minor_axis_length*pixel_size, mean_intensity=float(np.nanmean(intensity)))
            cells.append(base)
            from bactomate.modules.publication_figures import maxima_points
            local_foci=foci[(foci.frame==frame)&(foci._mask_label==r.label)] if foci is not None and not foci.empty else None
            samples.extend(maxima_points(base,coords,u,v,intensity,local_foci))
            # Separate longitudinal and 2D bins: each is averaged directly from raw pixels.
            xi = np.minimum(((u+1)*bins/2).astype(int), bins-1)
            yi = np.minimum(((v+1)*across/2).astype(int), across-1)
            tmp = pd.DataFrame(dict(xi=xi, yi=yi, intensity=intensity))
            for idx, vals in tmp.groupby('xi').intensity:
                samples.append(dict(**base, profile='longitudinal', position=-1+(idx+.5)*2/bins,
                                    transverse=np.nan, intensity=vals.mean(), pixel_count=vals.count()))
            for (i, j), vals in tmp.groupby(['xi', 'yi']).intensity:
                samples.append(dict(**base, profile='cell map', position=-1+(i+.5)*2/bins,
                                    transverse=-1+(j+.5)*2/across, intensity=vals.mean(), pixel_count=vals.count()))
    if not cells: raise ValueError('No cells with at least three pixels were found.')
    profiles=pd.DataFrame(samples)
    profiles['relative_position']=(profiles.position+1)/2
    profiles['relative_width']=profiles.transverse/2
    return pd.DataFrame(cells), profiles


def prepare(table, spec):
    if spec.kind not in KINDS: raise ValueError('Choose a supported figure type.')
    data = table.copy()
    if spec.filter_column:
        data = data[data[spec.filter_column].astype(str) == spec.filter_value]
    if spec.kind == 'Maxima map':
        from bactomate.modules.publication_figures import prepare_maxima
        return prepare_maxima(data,spec)
    if spec.kind == 'Demograph' and 'profile' in data:
        data = data[data.profile == 'longitudinal']
    if spec.kind == 'Kymograph' and 'profile' in data:
        data = data[data.profile == 'longitudinal']
    if spec.kind == 'Normalized cell heatmap' and 'profile' in data:
        data = data[data.profile == 'cell map']
    if data.empty: raise ValueError('No rows match the current selection.')
    if spec.kind == 'Correlation':
        numeric = data.select_dtypes(include='number').replace([np.inf, -np.inf], np.nan)
        numeric = numeric.dropna(axis=1, how='all')
        if len(numeric.columns) < 2: raise ValueError('Correlation needs at least two numeric metrics.')
        matrix = numeric.corr(min_periods=3)
        if not np.isfinite(matrix.to_numpy()).any(): raise ValueError('Correlation needs varying metrics and at least three paired observations.')
        return data, matrix, dict(xlabel='Metric (Pearson, pairwise n ≥ 3)', ylabel='Metric')
    required = [spec.x]
    if spec.kind in ('Scatter', 'Mean curve', 'Heatmap', 'Kymograph', 'Normalized cell heatmap'): required.append(spec.y)
    if spec.kind in ('Heatmap', 'Demograph', 'Kymograph', 'Normalized cell heatmap'): required.append(spec.value)
    if spec.kind == 'Demograph': required.append(spec.y)
    for column in required:
        if not column or column not in data: raise ValueError('Choose the required X, Y and Value columns.')
    numeric = [spec.x]
    if spec.kind in ('Scatter', 'Mean curve', 'Heatmap', 'Kymograph', 'Normalized cell heatmap'): numeric.append(spec.y)
    if spec.value and spec.kind in ('Heatmap', 'Demograph', 'Kymograph', 'Normalized cell heatmap'): numeric.append(spec.value)
    for column in set(numeric): data[column] = pd.to_numeric(data[column], errors='coerce')
    data = data.replace([np.inf, -np.inf], np.nan).dropna(subset=list(set(numeric)))
    if spec.minimum is not None: data = data[data[spec.x] >= spec.minimum]
    if spec.maximum is not None: data = data[data[spec.x] <= spec.maximum]
    if data.empty: raise ValueError('No finite values remain after filtering.')
    if spec.kind=='Demograph' and spec.relative_position:
        data[spec.x]=(data[spec.x]+1)/2
    group = data[spec.group].fillna('(missing)').astype(str) if spec.group else pd.Series('All', index=data.index)
    if spec.kind == 'Kymograph':
        if not spec.track_confirmed or not spec.group:
            raise ValueError('Kymographs need a verified track-ID column. Confirm that identities persist across time.')
        if group.nunique() != 1:
            raise ValueError('Filter to one track before drawing a kymograph. Do not combine unrelated cells.')
        if data[spec.y].nunique() < 2: raise ValueError('A kymograph requires at least two time points.')
        if any(c in data and data[c].nunique()!=1 for c in ('source','source_table')):
            raise ValueError('Select one source/XY for the kymograph.')
    labels = dict(xlabel=spec.x, ylabel=spec.y or 'Value')
    if spec.normalization != 'raw':
        if spec.kind not in ('Heatmap','Demograph','Kymograph','Normalized cell heatmap'):
            raise ValueError('Per-cell intensity normalization is available for spatial maps.')
        identity='object_key' if 'object_key' in data else spec.group
        if not identity: raise ValueError('Select an object-ID group for per-cell normalization.')
        data[spec.value+' (raw)']=data[spec.value]
        lo=data.groupby(identity)[spec.value].transform('min') if spec.normalization=='per-cell min-max' else 0
        hi=data.groupby(identity)[spec.value].transform('max')
        denom=hi-lo
        data[spec.value]=np.where(denom>0,(data[spec.value]-lo)/np.where(denom>0,denom,1),0)
    if spec.kind in ('Heatmap', 'Demograph', 'Kymograph', 'Normalized cell heatmap'):
        matrix = data.pivot_table(index=spec.y, columns=spec.x, values=spec.value, aggfunc='mean', sort=True)
        if spec.kind == 'Demograph' and spec.sort:
            order = data.groupby(spec.y)[spec.sort].first().sort_values(kind='stable').index
            matrix = matrix.reindex(order)
        if matrix.empty: raise ValueError('The selected coordinates do not form a matrix.')
        labels['colorlabel'] = spec.value + f' ({spec.normalization}; mean in bin)'
        return data, matrix, labels
    plot = pd.DataFrame({'x':data[spec.x], 'group':group})
    if spec.replicate:plot['replicate']=data[spec.replicate].fillna('').astype(str)
    if spec.kind in ('Scatter', 'Mean curve'): plot['y'] = data[spec.y]
    if spec.kind == 'Foci count':
        if (plot.x<0).any() or not np.allclose(plot.x,plot.x.round()):
            raise ValueError('Choose a non-negative integer foci count per cell, including cells with zero foci.')
        counts=range(int(plot.x.max())+1)
        chunks=[]
        for name,sub in plot.groupby('group',sort=True):
            frequencies=sub.x.value_counts().reindex(counts,fill_value=0)
            chunks.append(pd.DataFrame(dict(x=list(counts),y=100*frequencies.to_numpy()/len(sub),width=.8,group=name)))
        plot=pd.concat(chunks,ignore_index=True);labels=dict(xlabel='Number of foci per cell',ylabel='Cells (%)')
    elif spec.kind == 'Histogram':
        edges = np.histogram_bin_edges(plot.x, bins=spec.bins)
        chunks = []
        for name, sub in plot.groupby('group', sort=True):
            counts, _ = np.histogram(sub.x, bins=edges)
            chunks.append(pd.DataFrame(dict(x=(edges[:-1]+edges[1:])/2, y=counts,
                                            width=np.diff(edges), group=name)))
        plot = pd.concat(chunks, ignore_index=True); labels['ylabel'] = 'Count'
    elif spec.kind == 'Mean curve':
        plot = plot.groupby(['group','x'], as_index=False).agg(y=('y','mean'), n=('y','count'))
        labels['ylabel'] = spec.y + ' (mean)'
    elif spec.kind == 'ECDF':
        chunks = []
        for name, sub in plot.groupby('group', sort=True):
            values = np.sort(sub.x.to_numpy())
            chunks.append(pd.DataFrame(dict(x=values,y=np.arange(1,len(values)+1)/len(values),group=name)))
        plot = pd.concat(chunks, ignore_index=True); labels['ylabel'] = 'Cumulative fraction'
    elif spec.kind in ('Box plot', 'Violin plot'): labels = dict(xlabel=spec.group or 'Population', ylabel=spec.x)
    return data, plot, labels


def draw(figure, plot, spec, labels):
    figure.clear(); figure.set_size_inches(6,6,forward=False); ax = figure.subplots()
    matrix = spec.kind in ('Correlation','Heatmap','Demograph','Kymograph','Normalized cell heatmap')
    if spec.kind=='Maxima map':
        from bactomate.modules.publication_figures import draw_maxima
        draw_maxima(figure,ax,plot,spec,labels)
    elif matrix:
        image = ax.imshow(plot.to_numpy(dtype=float), aspect='auto', interpolation='nearest', cmap=spec.cmap)
        if spec.normalization!='raw':image.set_clim(0,1)
        cax=ax.inset_axes([1.04,0,.04,1])
        figure.colorbar(image,cax=cax,label=labels.get('colorlabel','Pearson r'))
        def ticks(values):
            idx = np.unique(np.linspace(0,len(values)-1,min(len(values),8)).astype(int))
            return idx, [str(values[i]) if len(str(values[i]))<=38 else '…'+str(values[i])[-35:] for i in idx]
        ax.set_xticks(*ticks(plot.columns)); ax.set_yticks(*ticks(plot.index))
        if spec.kind=='Demograph':
            cols=np.asarray(plot.columns,dtype=float)
            if spec.relative_position or spec.x=='relative_position':
                image.set_extent([0,1,len(plot),0]);ax.set_xticks([0,.5,1],['0','0.5','1'])
            else:ax.set_xticks(np.linspace(0,len(cols)-1,3),[f'{v:g}' for v in np.linspace(cols.min(),cols.max(),3)])
            ax.set_yticks([])
        if spec.kind=='Correlation': ax.tick_params(axis='x',rotation=60)
    else:
        groups = list(plot.groupby('group', sort=True))
        for i, (name, sub) in enumerate(groups):
            if spec.kind in ('Histogram','Foci count'): ax.bar(sub.x,sub.y,width=sub.width,alpha=.5,label=name)
            elif spec.kind == 'Scatter': ax.scatter(sub.x,sub.y,s=12,alpha=.7,label=name)
            elif spec.kind == 'Mean curve': ax.plot(sub.x,sub.y,label=name)
            elif spec.kind == 'ECDF': ax.step(sub.x,sub.y,where='post',label=name)
            elif spec.kind == 'Box plot': ax.boxplot([sub.x],positions=[i+1],manage_ticks=False)
            elif spec.kind == 'Violin plot':
                if sub.x.nunique() < 2: ax.scatter(np.full(len(sub),i+1),sub.x)
                else: ax.violinplot([sub.x],positions=[i+1],showmedians=True)
        if spec.kind in ('Box plot','Violin plot'): ax.set_xticks(range(1,len(groups)+1),[g[0] for g in groups])
        elif len(groups)>1: ax.legend()
        if spec.kind in ('Box plot','Violin plot') and spec.replicate and spec.show_replicates:
            names=[name for name,_ in groups]
            reps=sorted(plot.replicate.unique())
            for ri,rep in enumerate(reps):
                sub=plot[plot.replicate==rep].groupby('group').x.mean()
                offset=0 if len(reps)==1 else -.15+.3*ri/(len(reps)-1)
                ax.scatter([names.index(str(g))+1+offset for g in sub.index],sub.values,
                           s=38,label=str(rep),zorder=5)
            ax.legend(title='Replicate means')

    ax.set_box_aspect(2 if spec.kind=='Maxima map' else 1)
    if spec.kind=='Demograph':
        xlabel='Relative cell length' if spec.relative_position or spec.x=='relative_position' else labels['xlabel']
        labels.update(xlabel=xlabel+f'\n(n = {len(plot)} cells)',ylabel='Cells, sorted by length' if spec.sort=='length_um' else 'Cells')
    elif spec.kind=='Maxima map':
        count=plot.shape[0]
        labels.update(xlabel=labels['xlabel']+f'\n(n = {count} points)')
    ax.set(xlabel=labels['xlabel'],ylabel=labels['ylabel'],title=spec.title or spec.kind)
    figure.tight_layout()
    return ax


def export_bundle(folder, figure, used, plotted, spec, labels, *, formats=('png','pdf','svg'), provenance=None):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    figure.set_size_inches(6,6,forward=False)
    matrix = spec.kind in ('Correlation','Heatmap','Demograph','Kymograph','Normalized cell heatmap')
    used.to_csv(folder/'source_rows.csv',index=False)
    plotted.to_csv(folder/'plot_data.csv',index=matrix)
    with pd.ExcelWriter(folder/'figure_data.xlsx') as writer:
        used.to_excel(writer,sheet_name='Source rows',index=False)
        plotted.to_excel(writer,sheet_name='Plot data',index=matrix)
        if spec.replicate and spec.kind in ('Box plot','Violin plot'):
            summary=plotted.groupby(['group','replicate']).x.agg(['count','mean','std']).reset_index()
            summary.to_excel(writer,sheet_name='Replicates',index=False)
            summary.to_csv(folder/'replicate_summary.csv',index=False)
    config = dict(spec=asdict(spec),labels=labels,matrix=matrix,provenance=provenance or {},
                  missing='NaN: missing, never zero-filled',normalization=spec.normalization,
                  reproducibility='Scripts read the plotted values. Renderer/font differences are possible.')
    (folder/'figure.json').write_text(json.dumps(config,indent=2,ensure_ascii=False),encoding='utf8')
    for fmt in formats:
        if fmt not in ('png','pdf','svg'): raise ValueError('Unsupported figure format.')
        figure.savefig(folder/f'figure.{fmt}',dpi=300)
    # Export data-space drawing primitives so KDE/box statistics are identical
    # across languages without requiring BactoMate in the receiving environment.
    _write_scripts(folder, figure, labels, spec)
    hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file() and p.name!='manifest.json'}
    (folder/'manifest.json').write_text(json.dumps(hashes,indent=2))


def _write_scripts(folder, figure, labels, spec):
    """Export rendered data-space primitives so all languages share identical statistics."""
    from matplotlib.colors import to_rgba
    ax = figure.axes[0]; records=[]; index=0
    def add(kind, x, y, color, alpha=1):
        nonlocal index
        rgb = to_rgba(color)
        for a,b in zip(x,y): records.append(dict(element=index,kind=kind,x=float(a),y=float(b),r=rgb[0],g=rgb[1],b=rgb[2],alpha=alpha))
        index += 1
    for line in ax.lines:
        x,y = line.get_data()
        # Steps are expanded so R/MATLAB do not reinterpret their interpolation.
        vertices = line.get_path().vertices
        add('line',vertices[:,0],vertices[:,1],line.get_color())
        if line.get_marker() not in ('None','', ' '): add('point',x,y,line.get_color())
    for patch in ax.patches:
        verts = ax.transData.inverted().transform(patch.get_transform().transform(patch.get_path().vertices))
        add('polygon',verts[:,0],verts[:,1],patch.get_facecolor(),patch.get_alpha() or 1)
    for collection in ax.collections:
        from matplotlib.collections import PathCollection, PolyCollection
        colors=collection.get_facecolors()
        color=colors[0] if len(colors) else (0,0,0,1)
        if isinstance(collection,PathCollection):
            pts=np.asarray(collection.get_offsets()); add('point',pts[:,0],pts[:,1],color,collection.get_alpha() or 1)
        elif isinstance(collection,PolyCollection):
            for path in collection.get_paths(): add('polygon',path.vertices[:,0],path.vertices[:,1],color,collection.get_alpha() or 1)
        else:
            for segment in collection.get_segments(): add('line',segment[:,0],segment[:,1],collection.get_colors()[0])
    if ax.images:
        im=ax.images[0]; values=np.ma.asarray(im.get_array()); rgba=im.to_rgba(values)
        left,right,bottom,top=im.get_extent()
        xe=np.linspace(left,right,values.shape[1]+1)
        ye=np.linspace(top,bottom,values.shape[0]+1) if im.origin=='upper' else np.linspace(bottom,top,values.shape[0]+1)
        for row,col in np.ndindex(values.shape):
            if np.ma.is_masked(values[row,col]) or not np.isfinite(values[row,col]): continue
            add('polygon',[xe[col],xe[col+1],xe[col+1],xe[col]],[ye[row],ye[row],ye[row+1],ye[row+1]],rgba[row,col])
    geometry=pd.DataFrame(records,columns=['element','kind','x','y','r','g','b','alpha'])
    geometry.to_csv(folder/'figure_geometry.csv',index=False)
    meta=dict(box_aspect=ax.get_box_aspect(),xlim=list(ax.get_xlim()),ylim=list(ax.get_ylim()),title=spec.title or spec.kind,**labels,
              xticks=list(ax.get_xticks()),xticklabels=[t.get_text() for t in ax.get_xticklabels()],
              yticks=list(ax.get_yticks()),yticklabels=[t.get_text() for t in ax.get_yticklabels()])
    meta['legend'] = []
    handles,names=ax.get_legend_handles_labels()
    if ax.get_legend() is not None:
        for handle,name in zip(handles,names):
            color = handle.patches[0].get_facecolor() if hasattr(handle,'patches') and handle.patches else (handle.get_color() if hasattr(handle,'get_color') else (handle.get_facecolor()[0] if hasattr(handle,'get_facecolor') else '#444444'))
            if hasattr(color,'__len__') and not isinstance(color,str) and len(color) and hasattr(color[0],'__len__'): color=color[0]
            meta['legend'].append(dict(name=name,color=list(to_rgba(color)[:3])))
    meta['color_scale'] = None
    if ax.images:
        im=ax.images[0]
        meta['color_scale']=dict(lo=float(im.get_clim()[0]),hi=float(im.get_clim()[1]),label=labels.get('colorlabel','Pearson r'))
        pd.DataFrame(im.cmap(np.linspace(0,1,256))[:,:3],columns=['r','g','b']).to_csv(folder/'palette.csv',index=False)
    (folder/'axes.json').write_text(json.dumps(meta,indent=2,default=lambda v:v.item()))
    (folder/'reproduce.py').write_text('''"""Run: python reproduce.py (requires pandas, matplotlib). Geometry is data-derived."""
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent
d=pd.read_csv(root/'figure_geometry.csv'); m=json.loads((root/'axes.json').read_text())
fig,ax=plt.subplots(figsize=(6,6))
ax.set_box_aspect(m.get('box_aspect',1))
for _,g in d.groupby('element',sort=False):
    color=tuple(g.iloc[0][['r','g','b']]); kind=g.kind.iloc[0]; alpha=g.alpha.iloc[0]
    if kind=='polygon': ax.fill(g.x,g.y,color=color,alpha=alpha)
    elif kind=='point': ax.scatter(g.x,g.y,color=[color],s=12,alpha=alpha)
    else: ax.plot(g.x,g.y,color=color,alpha=alpha)
ax.set(xlim=m['xlim'],ylim=m['ylim'],title=m['title'],xlabel=m['xlabel'],ylabel=m['ylabel'])
ax.set_xticks(m['xticks'],m['xticklabels']); ax.set_yticks(m['yticks'],m['yticklabels'])
if m['legend']:
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([],[],color=g['color'],label=g['name']) for g in m['legend']])
if m['color_scale']:
    from matplotlib.colors import ListedColormap, Normalize
    from matplotlib.cm import ScalarMappable
    scale=m['color_scale']; palette=pd.read_csv(root/'palette.csv').to_numpy()
    cax=ax.inset_axes([1.04,0,.04,1])
    fig.colorbar(ScalarMappable(norm=Normalize(scale['lo'],scale['hi']),cmap=ListedColormap(palette)),cax=cax,label=scale['label'])
fig.tight_layout()
for ext in ('png','pdf','svg'): fig.savefig(root/('reproduced.'+ext),dpi=300)
''')
    (folder/'reproduce.R').write_text('''# Run in this bundle folder. Requires jsonlite. Uses precomputed geometry, no hidden KDE/statistics.
library(jsonlite)
d <- read.csv("figure_geometry.csv"); m <- fromJSON("axes.json")
render <- function() {
 plot(NA,xlim=m$xlim,ylim=m$ylim,xlab=m$xlabel,ylab=m$ylabel,main=m$title,axes=FALSE,xaxs="i",yaxs="i")
 axis(1,at=m$xticks,labels=m$xticklabels); axis(2,at=m$yticks,labels=m$yticklabels); box()
 for (id in unique(d$element)) {
  g <- d[d$element==id,]; col <- rgb(g$r[1],g$g[1],g$b[1],g$alpha[1])
  if (g$kind[1]=="polygon") polygon(g$x,g$y,col=col,border=NA)
  else if (g$kind[1]=="point") points(g$x,g$y,col=col,pch=16,cex=.5)
  else lines(g$x,g$y,col=col)
 }
 if (length(m$legend$name)) legend("topright",legend=m$legend$name,col=apply(m$legend$color,1,function(c) rgb(c[1],c[2],c[3])),lty=1)
 if (!is.null(m$color_scale)) {
  pal <- read.csv("palette.csv"); n <- nrow(pal); u <- par("usr")
  x <- u[2]+.03*diff(u[1:2]); w <- .03*diff(u[1:2]); yy <- seq(u[3],u[4],length.out=n+1)
  for (i in 1:n) rect(x,yy[i],x+w,yy[i+1],col=rgb(pal$r[i],pal$g[i],pal$b[i]),border=NA,xpd=NA)
  text(x+w,yy[c(1,n+1)],labels=c(m$color_scale$lo,m$color_scale$hi),pos=4,xpd=NA,cex=.7)
 }
}
pdf("reproduced_R.pdf",width=6,height=6); render(); dev.off()
png("reproduced_R.png",width=1800,height=1800,res=300); render(); dev.off()
svg("reproduced_R.svg",width=6,height=6); render(); dev.off()
''')
    (folder/'reproduce.m').write_text('''% Run from this bundle folder. Base MATLAB, readtable + jsondecode + exportgraphics.
d=readtable('figure_geometry.csv'); m=jsondecode(fileread('axes.json'));
figure('Units','inches','Position',[1 1 6 6]); hold on;
pbaspect([1 m.box_aspect 1]);
for id=unique(d.element)'
 g=d(d.element==id,:); c=[g.r(1),g.g(1),g.b(1)]; k=string(g.kind(1));
 if k=="polygon", patch(g.x,g.y,c,'EdgeColor','none','FaceAlpha',g.alpha(1));
 elseif k=="point", scatter(g.x,g.y,12,c,'filled');
 else, plot(g.x,g.y,'Color',c); end
end
xlim(sort(m.xlim)); ylim(sort(m.ylim));
if m.xlim(1)>m.xlim(2), set(gca,'XDir','reverse'); end
if m.ylim(1)>m.ylim(2), set(gca,'YDir','reverse'); end
xticks(m.xticks); xticklabels(m.xticklabels); yticks(m.yticks); yticklabels(m.yticklabels);
xlabel(m.xlabel); ylabel(m.ylabel); title(m.title);
if ~isempty(m.color_scale)
 p=readtable('palette.csv'); colormap([p.r,p.g,p.b]); caxis([m.color_scale.lo,m.color_scale.hi]); cb=colorbar; ylabel(cb,m.color_scale.label);
end
if ~isempty(m.legend)
 h=gobjects(length(m.legend),1);
 for j=1:length(m.legend), h(j)=plot(nan,nan,'Color',m.legend(j).color); end
 legend(h,{m.legend.name});
end
set(gcf,'PaperUnits','inches','PaperPosition',[0 0 6 6],'PaperSize',[6 6]);
print(gcf,'reproduced_MATLAB.pdf','-dpdf','-painters');
print(gcf,'reproduced_MATLAB.png','-dpng','-r300');
print(gcf,'reproduced_MATLAB.svg','-dsvg');
''')
