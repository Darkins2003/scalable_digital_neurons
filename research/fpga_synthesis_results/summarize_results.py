import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as pyplot
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from matplotlib.transforms import Bbox
import numpy


DIRECTORY = Path(__file__).resolve().parent
FAMILIES = {"Research": "01_research", "Maclaurin": "02_maclaurin", "Sollya": "03_sollya", "ROM": "04_rom"}
COLOURS = {"Research": "#d27724", "Maclaurin": "#2868b2", "Sollya": "#8155a5", "ROM": "#22825b"}
RESOURCES = (("total_luts", "Synthesis LUT count", "01_luts"), ("flip_flops", "Synthesis register count", "02_registers"), ("dsp_cells", "Synthesis DSP count", "03_dsps"), ("bram_tiles", "Synthesis BRAM tiles", "04_bram"))


def decimal_label(value, position=None):
    return numpy.format_float_positional(float(value), precision=6, unique=False, fractional=False, trim="-")


def describe(row):
    model = row["model"]
    family = "Research" if model in ("linear", "cubic") else "ROM" if model.startswith("bram_") else model.split("_")[0].capitalize()
    label = f"Research {model}" if family == "Research" else f"ROM, {int(model.split('_')[1]):,} entries" if family == "ROM" else f"{family}, degree {model.split('_')[1]}"
    implementation = {"logic": "logic", "lut": "LUT multiplication", "dsp": "DSP multiplication", "distributed": "LUT memory", "block": "BRAM"}[row["implementation"]]
    return family, f"{label} ({implementation})"


def load_rows(directory):
    settings = json.loads((directory / "run_configuration.json").read_text())
    if settings.get("output_fractional_bits") != 24 or settings.get("output_total_bits") != 32 or not settings.get("output_signed"):
        raise ValueError("This renderer requires new signed 32-bit Q24 FPGA measurements.")
    with (directory / "tables/resource_comparison.csv").open() as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        if row.get("resource_stage") != "post_synthesis" or int(row.get("input_fractional_bits", 0)) != 24 or int(row.get("output_fractional_bits", 0)) != 24 or int(row.get("output_total_bits", 0)) != 32 or row.get("output_signed") != "True":
            raise ValueError("Resource rows must contain Q24 post-synthesis measurements.")
        row["family"], row["label"] = describe(row)
        for key in ("total_luts", "flip_flops", "dsp_cells", "bram_tiles", "latency_cycles", "latency_ns", "mean_absolute_error", "maximum_absolute_error", "data_path_delay_ns", "setup_slack_ns", "hold_slack_ns"):
            row[key] = float(row[key]) if row.get(key) not in (None, "") else None
    rows.sort(key=lambda row: (list(FAMILIES).index(row["family"]), 1 if row["model"]=="linear" else 3 if row["model"]=="cubic" else int(row["model"].split("_")[1]), row["implementation"]))
    for number, row in enumerate(rows, 1):
        row["point"] = number
    return settings, rows


def ticks(axis, values, horizontal=False, logarithmic=False, integer=False):
    values = [float(value) for value in values if value is not None]
    lower = min([0, *values])
    upper = max([0, *values])
    if logarithmic and values and min(values)>0:
        lower = 10**math.floor(math.log10(min(values)))
        upper = 10**math.ceil(math.log10(max(values)))
        upper = max(upper, lower*10)
        positions = numpy.geomspace(lower, upper, 6)
        axis.set_yscale("log")
        axis.set_yticks(positions)
        axis.set_ylim(lower, upper)
        axis.minorticks_off()
    else:
        span = upper-lower if upper>lower else 1
        target = max(1,span*1.12/5) if integer else span*1.12/5
        scale = 10**math.floor(math.log10(target))
        increment = next(value for value in (1,1.5,2,2.5,3,4,5,6,8,10) if value>=target/scale)*scale
        if integer:
            increment = math.ceil(increment)
        lower = math.floor(lower/increment)*increment
        while lower+5*increment<upper:
            increment *= 2
            lower = math.floor(lower/increment)*increment
        positions = lower+numpy.arange(6)*increment
        if horizontal:
            axis.set_xticks(positions)
            axis.set_xlim(positions[0], positions[-1])
        else:
            axis.set_yticks(positions)
            axis.set_ylim(positions[0], positions[-1])
    (axis.xaxis if horizontal else axis.yaxis).set_major_formatter(FuncFormatter(decimal_label))


def place_point_labels(axis, groups):
    figure = axis.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    occupied = []
    marker_positions = [axis.transData.transform(position) for position in groups]
    for position, numbers in sorted(groups.items(), key=lambda item: item[0][1], reverse=True):
        label = ",".join(numbers) if len(numbers)<=3 else numbers[0]+" + shared"
        width,height,unused = renderer.get_text_width_height_descent(label, matplotlib.font_manager.FontProperties(size=8), False)
        anchor = axis.transData.transform(position)
        best = None
        for radius in (7,16,28,42,60,85,115,150):
            for horizontal,vertical in ((radius,radius/2),(radius,-radius/2),(-radius,radius/2),(-radius,-radius/2),(0,radius),(0,-radius)):
                centre = anchor + numpy.array([horizontal,vertical])*figure.dpi/72
                left = centre[0]-width if horizontal<0 else centre[0]-width/2 if horizontal==0 else centre[0]
                bottom = centre[1]-height if vertical<0 else centre[1]
                box = Bbox.from_bounds(left-3,bottom-3,width+6,height+6)
                overlaps = sum(box.overlaps(previous) for previous in occupied)
                covers = sum(box.contains(*point) for point in marker_positions)
                outside = max(0,axis.bbox.x0-box.x0)+max(0,box.x1-axis.bbox.x1)+max(0,axis.bbox.y0-box.y0)+max(0,box.y1-axis.bbox.y1)
                score = overlaps*1000000+covers*100000+outside*100000000+horizontal**2+vertical**2
                if best is None or score<best[0]:
                    best = (score,horizontal,vertical,box)
        unused,horizontal,vertical,box = best
        axis.annotate(label,position,xytext=(horizontal,vertical),textcoords="offset points",ha="right" if horizontal<0 else "center" if horizontal==0 else "left",va="top" if vertical<0 else "bottom",fontsize=8,arrowprops={"arrowstyle":"-","lw":.4,"color":"#94a3b8"})
        occupied.append(box)


def save(figure, destination, title, clock, note, point_labels=None):
    height = figure.get_size_inches()[1]
    figure.suptitle(title, fontsize=16, y=1-.12/height)
    figure.text(.5,1-.55/height,f"24 fractional input bits | signed 32-bit Q24 output | {clock:g} MHz",ha="center",fontsize=10)
    figure.text(.5,.15/height,note,ha="center",fontsize=9)
    figure.tight_layout(rect=(0,.5/height,1,1-.95/height))
    if point_labels is not None:
        place_point_labels(*point_labels)
    destination.parent.mkdir(parents=True,exist_ok=True)
    figure.savefig(destination,dpi=160,facecolor="white")
    pyplot.close(figure)


def table_plot(rows, destination, clock, accuracy=False):
    columns = ["Model", "Mean absolute error", "Maximum absolute error", "Path delay (ns)", "Setup slack (ns)", "Hold slack (ns)", "Timing"] if accuracy else ["Model", "LUTs", "Registers", "DSPs", "BRAM tiles", "Latency (cycles)", "Latency (ns)", "Mapping"]
    fields = ["mean_absolute_error", "maximum_absolute_error", "data_path_delay_ns", "setup_slack_ns", "hold_slack_ns"] if accuracy else ["total_luts", "flip_flops", "dsp_cells", "bram_tiles", "latency_cycles", "latency_ns"]
    cells = [[row["label"],*[decimal_label(row[field]) if row[field] is not None else "Unavailable" for field in fields],*(["PASS" if row["timing_pass"]=="True" else "FAIL"] if accuracy else ["Matches" if row["mapping_matches_request"]=="True" else "CHECK"])] for row in rows]
    figure,axis = pyplot.subplots(figsize=(18,max(5.5,.36*len(rows)+2.5)))
    axis.axis("off")
    widths = [.46]+[(1-.46)/(len(columns)-1)]*(len(columns)-1)
    table = axis.table(cellText=cells,colLabels=columns,cellLoc="center",colWidths=widths,bbox=(0,0,1,1))
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (position,column),cell in table.get_celld().items():
        cell.set_edgecolor("#d3dce5")
        cell.set_linewidth(.5)
        cell.set_facecolor("#20364d" if position==0 else "#f1f5f9" if position%2 else "white")
        if position==0:
            cell.set_text_props(color="white",weight="bold")
    save(figure,destination,"Accuracy and routed timing" if accuracy else "Synthesis resources and latency",clock,"Accuracy uses matching Q24 Python results. Timing is post-route." if accuracy else "Resources are post-synthesis. BRAM tiles are 36-Kbit equivalents; 0.5 tile means one RAMB18.")


def bar_plot(rows, field, label, destination, clock):
    selected = [row for row in rows if row.get(field) is not None]
    if not selected:
        return
    figure,axis = pyplot.subplots(figsize=(14,max(5.5,.30*len(selected)+2.5)))
    values = [row[field] for row in selected]
    axis.barh(range(len(selected)),values,color=[COLOURS[row["family"]] for row in selected])
    axis.set(yticks=range(len(selected)),yticklabels=[row["label"] for row in selected],xlabel=label)
    axis.invert_yaxis()
    axis.tick_params(axis="y",labelsize=8)
    ticks(axis,values,horizontal=True,integer=field in ("total_luts","flip_flops","dsp_cells","latency_cycles"))
    axis.grid(axis="x",alpha=.2)
    axis.spines[["top","right"]].set_visible(False)
    for position,row in enumerate(selected):
        axis.annotate(decimal_label(row[field])+(" [timing FAIL]" if row["timing_pass"]!="True" else "")+(" [mapping CHECK]" if row["mapping_matches_request"]!="True" else ""),(row[field],position),xytext=(4,0),textcoords="offset points",va="center",fontsize=8)
    save(figure,destination,label,clock,"All measured designs are included. Resource counts are from synthesis; path delay and slack are from routing.")


def scatter_plot(rows, field, horizontal_label, error_field, destination, clock):
    selected = [row for row in rows if row.get(field) is not None and row.get(error_field) is not None]
    if not selected:
        return
    figure,(axis,key) = pyplot.subplots(1,2,figsize=(17,max(6,.28*len(selected)+2.5)),gridspec_kw={"width_ratios":[1,1.35]})
    points = {}
    for row in selected:
        passed = row["timing_pass"]=="True"
        axis.scatter(row[field],row[error_field],color=COLOURS[row["family"]] if passed else "#b91c1c",marker="o" if passed else "x",s=45,zorder=3)
        points.setdefault((row[field],row[error_field]),[]).append(str(row["point"]))
    axis.set(xlabel=horizontal_label,ylabel=("Mean" if error_field.startswith("mean") else "Maximum")+" absolute error (log scale)")
    ticks(axis,[row[field] for row in selected],horizontal=True,integer=field in ("total_luts","flip_flops","dsp_cells","latency_cycles"))
    ticks(axis,[row[error_field] for row in selected],logarithmic=True)
    axis.grid(alpha=.2)
    axis.spines[["top","right"]].set_visible(False)
    key.axis("off")
    cells = [[row["point"],row["label"],decimal_label(row["dsp_cells"]),decimal_label(row["bram_tiles"])] for row in selected]
    table=key.table(cellText=cells,colLabels=["No.","Model","DSPs","BRAM"],colWidths=[.07,.71,.1,.12],cellLoc="left",bbox=(0,0,1,1))
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    for (position,column),cell in table.get_celld().items():
        cell.set_linewidth(.3)
        cell.set_edgecolor("#d3dce5")
        cell.set_facecolor("#e2e8f0" if position==0 else "white")
    save(figure,destination,("Mean" if error_field.startswith("mean") else "Maximum")+" absolute error versus "+horizontal_label,clock,"Lower error is better. Red crosses failed routed timing. Point numbers match the full model names in the key.",point_labels=(axis,points))


def model_size_plots(rows, images, clock):
    for family in ("Maclaurin","Sollya","ROM"):
        selected = [row for row in rows if row["family"]==family]
        if not selected:
            continue
        destination = images/"05_accuracy_vs_model_size"/FAMILIES[family]
        positions = lambda row: int(row["model"].split("_")[1])
        unique = {row["model"]:row for row in selected}
        models = sorted(unique.values(),key=positions)
        figure,axes = pyplot.subplots(1,2,figsize=(13,6))
        for axis,field,title in zip(axes,("mean_absolute_error","maximum_absolute_error"),("Mean absolute error","Maximum absolute error")):
            axis.plot([positions(row) for row in models],[row[field] for row in models],"o-")
            ticks(axis,[row[field] for row in models],logarithmic=True)
            axis.set(xlabel="Stored entries" if family=="ROM" else "Polynomial degree",ylabel=title+" (log scale)")
            axis.grid(alpha=.2)
            if family=="ROM":
                axis.set_xscale("log",base=2)
                axis.set_xticks([positions(row) for row in models][::2],[f"{positions(row):,}" for row in models][::2],rotation=30)
            else:
                axis.set_xticks(range(5))
        save(figure,destination/"01_accuracy.png",family+": accuracy versus model size",clock,"Accuracy is shared by numerically equivalent implementations. Statistics cover the saved Q24 test inputs; no plotting bins.")
        figure,axes = pyplot.subplots(2,3,figsize=(16,10))
        for axis,(field,title) in zip(axes.flat,[(field,label) for field,label,unused in RESOURCES]+[("latency_cycles","Latency (cycles)"),("data_path_delay_ns","Routed data-path delay (ns)")]):
            for implementation in sorted({row["implementation"] for row in selected}):
                group=sorted([row for row in selected if row["implementation"]==implementation and row.get(field) is not None],key=positions)
                axis.plot([positions(row) for row in group],[row[field] for row in group],"o-",label={"logic":"Logic","lut":"LUT multiplication","dsp":"DSP multiplication","distributed":"LUT memory","block":"BRAM"}[implementation])
            ticks(axis,[row[field] for row in selected if row.get(field) is not None],integer=field in ("total_luts","flip_flops","dsp_cells","latency_cycles"))
            axis.set(xlabel="Stored entries" if family=="ROM" else "Polynomial degree",ylabel=title)
            if family=="ROM":
                axis.set_xscale("log",base=2)
                axis.set_xticks([positions(row) for row in models][::2],[f"{positions(row):,}" for row in models][::2],rotation=30)
            else:
                axis.set_xticks(range(5))
            axis.grid(alpha=.2)
            axis.legend(fontsize=8)
        save(figure,destination/"02_resources_and_latency.png",family+": cost versus model size",clock,"Resources are post-synthesis. Timing comes from routing. Passing the selected clock is not a maximum-frequency measurement.")


def summarize(directory):
    settings,rows = load_rows(directory)
    if not rows:
        raise ValueError("No completed Q24 measurements to plot.")
    clock=float(settings["clock_mhz"])
    images=directory/"images"
    groups=[("00_all_models",rows)]+[(folder,[row for row in rows if row["family"]==family]) for family,folder in FAMILIES.items()]
    for folder,selected in groups:
        if not selected:
            continue
        table_plot(selected,images/"00_tables"/folder/"01_resources_and_latency.png",clock)
        table_plot(selected,images/"00_tables"/folder/"02_accuracy_and_timing.png",clock,accuracy=True)
        for field,label,filename in RESOURCES:
            bar_plot(selected,field,label,images/"01_resource_usage"/folder/(filename+".png"),clock)
        for field,label,filename in (("latency_cycles","Latency (cycles)","01_cycles.png"),("latency_ns","Latency (ns)","02_nanoseconds.png")):
            bar_plot(selected,field,label,images/"02_latency"/folder/filename,clock)
        for error_field,category in (("mean_absolute_error","01_mean_absolute_error"),("maximum_absolute_error","02_maximum_absolute_error")):
            for field,label,filename in RESOURCES:
                scatter_plot(selected,field,label,error_field,images/"03_accuracy_vs_resources"/category/folder/(filename+".png"),clock)
            scatter_plot(selected,"latency_ns","Latency (ns)",error_field,images/"04_accuracy_vs_latency"/category/folder/"01_comparison.png",clock)
        for field,label,filename in (("data_path_delay_ns","Routed data-path delay (ns)","01_path_delay.png"),("setup_slack_ns","Routed setup slack (ns)","02_setup_slack.png")):
            bar_plot(selected,field,label,images/"06_routed_timing"/folder/filename,clock)
    model_size_plots(rows,images,clock)
    report=[f"# Q24 FPGA synthesis results at {clock:g} MHz","",f"Completed: {len(rows)} of 47 designs. Routed setup and hold timing passes: {sum(row['timing_pass']=='True' for row in rows)}.","","Input: 24 fractional bits, 0 <= f < 1. Output: signed 32-bit, 24 fractional bits. No integer shift or Q8 conversion. Resources: post-synthesis. Timing: post-route. Latency: elapsed clock periods from input acceptance to output. All designs accept one input per cycle.","","| Model | LUTs | Registers | DSPs | BRAM tiles | Latency cycles | Latency ns | Mean absolute error | Maximum absolute error | Path delay ns | Setup slack ns | Hold slack ns | Routed timing | Mapping |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for row in rows:
        report.append("| "+" | ".join([row["label"],*[decimal_label(row[field]) for field in ("total_luts","flip_flops","dsp_cells","bram_tiles","latency_cycles","latency_ns","mean_absolute_error","maximum_absolute_error","data_path_delay_ns","setup_slack_ns","hold_slack_ns")],"PASS" if row["timing_pass"]=="True" else "FAIL","Matches" if row["mapping_matches_request"]=="True" else "CHECK"])+" |")
    report.extend(["","Accuracy means use the uniform Q24 population; maxima include directed boundaries. Errors compare the output against unquantised 2^f. LUT/DSP and distributed/BRAM variants share accuracy only after bit-exact RTL validation. The research cubic retains its Q24 linear term.","","The achievable frequency has not been established by passing this clock. Compare routed path delays and repeat measurements with tighter constraints. Slack-derived frequency is an estimate, not a verified maximum. These are standalone cores, not integrated system timing.",""])
    (directory/"tables/comparison_summary.md").write_text("\n".join(report))
    (directory/"README.md").write_text(f"# Q24 FPGA results at {clock:g} MHz\n\nCompleted measurements: {len(rows)} of 47. See tables/comparison_summary.md for the full comparison and images/README.md for plot categories. Resources are post-synthesis; timing is post-route. Accuracy uses the saved signed 32-bit Q24 reference under tables/accuracy_reference. Previous Q8 results remain in ../../archive/q8.\n")
    (images/"README.md").write_text("# Q24 FPGA plots\n\n00_tables: full results, plus tables grouped by family.\n01_resource_usage: synthesis LUTs, registers, DSPs and BRAM.\n02_latency: cycles and nanoseconds.\n03_accuracy_vs_resources: mean and maximum absolute error versus each resource.\n04_accuracy_vs_latency: mean and maximum absolute error versus latency.\n05_accuracy_vs_model_size: increasing polynomial degree or ROM entries.\n06_routed_timing: path delay and setup slack, kept separate from synthesis resources.\n\nMost categories contain 00_all_models, 01_research, 02_maclaurin, 03_sollya and 04_rom. Accuracy scatter plots have numbered points and full-name keys. Error axes use logarithmic spacing to show small values. Every plot uses matching Q24 measurements. No ideal-resource branch exists because FPGA resources describe fixed-point hardware.\n")
    print(f"Saved organised Q24 tables and plots for {len(rows)} measured designs: {images}",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Regenerate organised Q24 FPGA plots from completed measurements.")
    parser.add_argument("directory",nargs="?",type=Path,default=DIRECTORY/"results/250MHz")
    summarize(parser.parse_args().directory.resolve())
