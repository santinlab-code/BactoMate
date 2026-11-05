"""Length-preserving demographs and normalized fluorescence maps."""
import numpy as np
import pandas as pd
from bactomate.modules.cell_coordinates import capsule_radius, capsule_outline


def length_demograph(data, spec):
    length_column = spec.sort or ('axis_length_um' if 'axis_length_um' in data else 'length_um')
    if length_column not in data:
        raise ValueError('A length-scaled demograph needs a measured cell-length column.')
    lengths = pd.to_numeric(data[length_column], errors='coerce').groupby(data[spec.y]).first()
    if not np.isfinite(lengths).all() or (lengths <= 0).any():
        raise ValueError('Cell lengths must be finite and positive.')
    lengths = lengths.sort_values(kind='stable')
    relative = spec.x == 'relative_position' or spec.relative_position
    if 'longitudinal_bins' in data and data.longitudinal_bins.nunique() == 1:
        count = int(data.longitudinal_bins.iloc[0])
        grid = (np.arange(count)+.5)/count
        if not relative: grid = 2*grid-1
    else:
        grid = np.sort(data[spec.x].unique())
    profiles = data.pivot_table(index=spec.y, columns=spec.x, values=spec.value, aggfunc='mean').reindex(index=lengths.index)
    # Round coordinate labels only for lookup of equivalent exported bin centres.
    profiles.columns = np.round(profiles.columns.astype(float), 10)
    profiles = profiles.reindex(columns=np.round(grid, 10))
    position = np.linspace(-1, 1, 257)
    values = np.full((len(position), len(lengths)), np.nan)
    normalized_grid = grid if relative else (grid+1)/2
    edges = np.r_[0., (normalized_grid[:-1]+normalized_grid[1:])/2, 1.]
    maximum = float(lengths.max())
    for col, (identity, length) in enumerate(lengths.items()):
        scale = float(length)/maximum
        source = (1-position/scale)/2  # Pole 0 is at the top, as in the reference cell.
        inside = np.abs(position) <= scale
        bins = np.clip(np.searchsorted(edges, source, side='right')-1, 0, len(grid)-1)
        values[inside, col] = profiles.loc[identity].to_numpy(float)[bins[inside]]
    used = data.copy()
    used['demograph_order'] = used[spec.y].map({key:i+1 for i,key in enumerate(lengths.index)})
    used['demograph_length_um'] = used[spec.y].map(lengths)
    labels = dict(xlabel=f'Cells, ordered by length\n(n = {len(lengths)} cells)',
                  ylabel='Centered position / half-length of longest cell',
                  colorlabel=('Local cell width (µm)' if spec.value == 'local_width_um' else
                              spec.value+f' ({spec.normalization}; mean in bin)'),
                  length_column=length_column, longest_cell_um=maximum)
    return used, pd.DataFrame(values, index=position, columns=lengths.index), labels


def draw_length_demograph(figure, ax, plot, spec, labels):
    image = ax.imshow(plot.to_numpy(float), extent=[0,len(plot.columns),-1,1],
                      origin='lower', cmap=spec.cmap, aspect='auto', interpolation='nearest')
    if spec.normalization != 'raw': image.set_clim(0,1)
    ax.set_yticks([-1,-.5,0,.5,1])
    ax.axhline(0, color='.65', linewidth=.6)
    cax=ax.inset_axes([1.04,0,.04,1])
    figure.colorbar(image,cax=cax,label=labels['colorlabel'])
    return image


def draw_cell_heatmap(figure, ax, plot, spec, labels):
    if not np.all((np.asarray(plot.columns,float)>=-.5)&(np.asarray(plot.columns,float)<=.5)):
        raise ValueError('Reference-cell maps need relative width −0.5…0.5 for X.')
    if not np.all((np.asarray(plot.index,float)>=0)&(np.asarray(plot.index,float)<=1)):
        raise ValueError('Reference-cell maps need relative length 0…1 for Y.')
    x,y=np.meshgrid(np.asarray(plot.columns,float),np.asarray(plot.index,float))
    values=plot.to_numpy(float).copy()
    values[np.abs(x)>capsule_radius(y)]=np.nan
    image=ax.imshow(values,extent=[-.5,.5,0,1],origin='lower',aspect='auto',
                    interpolation='nearest',cmap=spec.cmap)
    if spec.normalization!='raw':image.set_clim(0,1)
    outline_x,outline_y=capsule_outline()
    ax.plot(outline_x,outline_y,color='white' if spec.map_background=='black' else '.25',linewidth=spec.line_width)
    ax.set_xlim(-.58,.58);ax.set_ylim(1.05,-.05)
    ax.set_xticks([-.5,0,.5]);ax.set_yticks([0,.2,.4,.6,.8,1])
    cax=ax.inset_axes([1.04,0,.04,1])
    figure.colorbar(image,cax=cax,label=labels['colorlabel'])
    return image
