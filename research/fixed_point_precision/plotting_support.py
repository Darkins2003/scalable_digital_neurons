from __future__ import annotations

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def number(value, digits=3):
    if value is None or value == '':
        return '—'
    value = float(value)
    if value == 0:
        return '0'
    if abs(value) >= 10000 or abs(value) < .001:
        return f'{value:.2e}'
    return f'{value:.{digits}g}'


def png_table(path, title, subtitle, columns, rows, footer, widths=None, row_colours=None, cell_colours=None, figure_width=16):
    path.parent.mkdir(parents=True, exist_ok=True)
    height = max(4.0, 2.0 + .32 * (len(rows) + 1))
    figure = plt.figure(figsize=(figure_width, height), facecolor='white')
    figure.text(.035, .965, title, fontsize=19, fontweight='bold', color='#172b40', va='top')
    figure.text(.035, .91, subtitle, fontsize=10.5, color='#4c5d70', va='top')
    axis = figure.add_axes([.03, .16, .94, .67])
    axis.axis('off')
    table = axis.table(cellText=rows, colLabels=columns, cellLoc='center', colWidths=widths, bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    for (row, column), cell in table.get_celld().items():
        cell.set_linewidth(.45)
        cell.set_edgecolor('#d5dce4')
        if row == 0:
            cell.set_facecolor('#203b55')
            cell.set_text_props(color='white', weight='bold', fontsize=10)
            cell.set_height(cell.get_height() * 1.6)
        else:
            cell.set_facecolor('#f0f4f8' if row % 2 else 'white')
            if column == 0:
                cell.set_text_props(ha='left', color='#182b3e')
                if row_colours:
                    cell.set_text_props(color=row_colours[row - 1], weight='bold')
            if cell_colours and (row - 1, column) in cell_colours:
                cell.set_facecolor(cell_colours[(row - 1, column)])
    figure.text(.035, .055, footer, fontsize=9.5, color='#46596c', va='bottom', linespacing=1.5)
    figure.savefig(path, dpi=180, facecolor='white')
    plt.close(figure)


def decorate(axis, ylabel=None):
    axis.grid(alpha=.22, linewidth=.6)
    axis.spines[['top', 'right']].set_visible(False)
    if ylabel:
        axis.set_ylabel(ylabel)


def save_figure(figure, destination):
    figure.savefig(destination, dpi=180, facecolor='white')
    plt.close(figure)
