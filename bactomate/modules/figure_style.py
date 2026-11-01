"""Plot styling stored in FigureSpec and exported with the source data."""
import numpy as np


def ordered_groups(plot,spec):
    groups={str(name):sub for name,sub in plot.groupby('group',sort=True)}
    order=[name for name in spec.group_order if name in groups]
    order += [name for name in groups if name not in order]
    return [(name,groups[name]) for name in order]


def apply_style(figure,ax,spec):
    if not spec.show_title:ax.set_title('')
    if spec.xlabel:ax.set_xlabel(spec.xlabel)
    if spec.ylabel:ax.set_ylabel(spec.ylabel)
    if spec.x_min is not None or spec.x_max is not None:ax.set_xlim(left=spec.x_min,right=spec.x_max)
    if spec.y_min is not None or spec.y_max is not None:ax.set_ylim(bottom=spec.y_min,top=spec.y_max)
    ax.tick_params(axis='x',labelrotation=spec.x_tick_rotation,labelsize=spec.font_size)
    ax.tick_params(axis='y',labelsize=spec.font_size)
    ax.xaxis.label.set_fontsize(spec.font_size);ax.yaxis.label.set_fontsize(spec.font_size)
    ax.title.set_fontsize(spec.font_size+2)
    for line in ax.lines:line.set_linewidth(spec.line_width)
    for patch in ax.patches:patch.set_linewidth(spec.line_width)
    ax.set_axisbelow(True)
    if spec.show_grid:ax.grid(True,alpha=.25)
    else:ax.grid(False)
    if not spec.show_legend and ax.get_legend() is not None:ax.get_legend().remove()
    elif ax.get_legend() is not None:
        for text in ax.get_legend().get_texts():text.set_fontsize(spec.font_size)
    if ax.images and (spec.colorbar_min is not None or spec.colorbar_max is not None):
        lo,hi=ax.images[0].get_clim()
        lo=lo if spec.colorbar_min is None else spec.colorbar_min
        hi=hi if spec.colorbar_max is None else spec.colorbar_max
        if hi<=lo:raise ValueError('Colour scale maximum must exceed its minimum.')
        ax.images[0].set_clim(lo,hi)
    for child in ax.child_axes:
        child.tick_params(labelsize=spec.font_size)
        child.yaxis.label.set_fontsize(spec.font_size)
