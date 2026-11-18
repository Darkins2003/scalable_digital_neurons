import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as pyplot
from matplotlib.ticker import FuncFormatter
import numpy

import compare_base_two_exponential as comparison


CATEGORIES = ("01_signed_error", "02_absolute_error", "03_mean_absolute_error", "04_maximum_absolute_error")


def number_label(value, position):
    return numpy.format_float_positional(value, precision=6, unique=False, fractional=False, trim="-")


def model_name(name, fixed_point=False):
    if name == "linear":
        return "Research linear"
    if name == "cubic":
        return "Research cubic (Q24 variant)" if fixed_point else "Research cubic"
    return comparison.model_label(name)


def file_name(name):
    if name.startswith("bram_"):
        return f"rom_{name.split('_')[1]}_entries.png"
    if name in ("linear", "cubic"):
        return f"research_{name}.png"
    family, degree = name.split("_")
    return f"{family}_degree_{degree}.png"


def model_folder(name):
    if name in ("linear", "cubic"):
        return "01_research"
    if name.startswith("maclaurin_"):
        return "02_maclaurin"
    if name.startswith("sollya_"):
        return "03_sollya"
    if name.startswith("bram_"):
        return "04_rom"
    raise ValueError(f"Unknown model: {name}")


def style_axis(axis, values, signed=False):
    lower = float(numpy.min(values)) if signed else 0
    upper = float(numpy.max(values))
    comparison.signed_error_ticks(axis, lower, upper)
    axis.xaxis.set_major_formatter(FuncFormatter(number_label))
    axis.grid(alpha=.2)
    axis.spines[["top", "right"]].set_visible(False)
    if signed:
        axis.axhline(0, color="#7a7a7a", linewidth=.7)


def finish(figure, destination, title, evaluation, note, legend_space=False):
    for label in list(figure.texts):
        if label is not figure._suptitle:
            label.remove()
    figure.suptitle(title, fontsize=16, y=.98)
    figure.text(.5,.90,evaluation,ha="center",fontsize=11)
    figure.text(.5,.025,note,ha="center",fontsize=9)
    figure.tight_layout(rect=(0,.32 if legend_space else .09,1,.83))
    destination.parent.mkdir(parents=True,exist_ok=True)
    figure.savefig(destination,dpi=160,facecolor="white")
    pyplot.close(figure)


def save_error_category(directory, category, inputs, centres, errors, mean_profiles, maximum_profiles, names, colours, evaluation, fixed_point, bins):
    signed = category == "01_signed_error"
    binned = category in ("03_mean_absolute_error", "04_maximum_absolute_error")
    values = errors if signed else {name:numpy.abs(errors[name]) for name in names} if not binned else mean_profiles if category == "03_mean_absolute_error" else maximum_profiles
    horizontal = centres if binned else inputs
    ylabel = {"01_signed_error":"Signed error (output units)", "02_absolute_error":"Absolute error (output units)", "03_mean_absolute_error":"Mean absolute error per display bin", "04_maximum_absolute_error":"Maximum absolute error per display bin"}[category]
    note = f"Display subset: 262,144 uniform inputs plus ROM boundaries and neighbours; {bins} bins. Full-test statistics are in the tables." if binned else "Individual display inputs; no bin averaging. Display subset includes uniform inputs and ROM boundaries with neighbours."
    for name in names:
        rom = name.startswith("bram_") and not binned
        figure, axes = pyplot.subplots(1,2 if rom else 1,figsize=(13,5.5) if rom else (11,5.5))
        axes = list(axes) if rom else [axes]
        axes[0].plot(horizontal,values[name],color=colours[name],linewidth=1)
        axes[0].set(xlabel="Fractional exponent f",ylabel=ylabel,xlim=(0,1))
        style_axis(axes[0],values[name],signed)
        if rom:
            entries = int(name.split("_")[1])
            limit = min(4/entries,float(inputs[-1]))
            selected = inputs <= limit
            axes[1].plot(inputs[selected],values[name][selected],color=colours[name],linewidth=1.3)
            axes[1].set(xlabel="Fractional exponent f",ylabel=ylabel,xlim=(0,limit),title="First four ROM address intervals")
            style_axis(axes[1],values[name][selected],signed)
        finish(figure,directory/category/model_folder(name)/file_name(name),model_name(name,fixed_point)+": "+ylabel,evaluation,note)
    figure,axis = pyplot.subplots(figsize=(14,8))
    for position,name in enumerate(names):
        axis.plot(horizontal,values[name],color=colours[name],linestyle="--" if position>=20 else "-",linewidth=1,label=model_name(name,fixed_point))
    axis.set(xlabel="Fractional exponent f",ylabel=ylabel,xlim=(0,1))
    style_axis(axis,numpy.concatenate([values[name] for name in names]),signed)
    figure.legend(*axis.get_legend_handles_labels(),loc="lower center",bbox_to_anchor=(.5,.075),ncol=4,fontsize=8,frameon=False)
    finish(figure,directory/category/"00_comparisons"/"00_all_models_comparison.png","All models: "+ylabel,evaluation,note,legend_space=True)


def summary_value(rows, name, domain, maximum):
    selected = [row for row in rows if row["model"]==name and row["domain"]==domain]
    if maximum:
        return max(float(row["maximum_absolute_error"]) for row in selected)
    return float(next(row["mean_absolute_error"] for row in selected if row["population"]=="uniform"))


def save_model_size_plots(directory, rows, domain, names, evaluation, fixed_point):
    groups = []
    roms = sorted((name for name in names if name.startswith("bram_")),key=lambda name:int(name.split("_")[1]))
    groups.append(("01_rom_table_size.png","ROM accuracy versus table size",[("ROM",roms)],True))
    for position,family in ((2,"maclaurin"),(3,"sollya")):
        models = sorted((name for name in names if name.startswith(family+"_")),key=lambda name:int(name.split("_")[1]))
        groups.append((f"{position:02d}_{family}_degree.png",family.capitalize()+" accuracy versus polynomial degree",[(family.capitalize(),models)],False))
    groups.append(("04_polynomial_comparison.png","Polynomial accuracy versus degree",[("Maclaurin",[name for name in names if name.startswith("maclaurin_")]),("Sollya",[name for name in names if name.startswith("sollya_")]),("Research",[name for name in names if name in ("linear","cubic")])],False))
    for filename,title,series,rom in groups:
        figure,axes = pyplot.subplots(1,2,figsize=(13,5.5),sharey=True)
        plotted = []
        for axis,maximum in zip(axes,(False,True)):
            for label,models in series:
                if not models:
                    continue
                models = sorted(models,key=lambda name:1 if name=="linear" else 3 if name=="cubic" else int(name.split("_")[1]))
                positions = [int(name.split("_")[1]) if rom else 1 if name=="linear" else 3 if name=="cubic" else int(name.split("_")[1]) for name in models]
                errors = [summary_value(rows,name,domain,maximum) for name in models]
                axis.plot(positions,errors,"o" if label=="Research" else "o-",label=label,linewidth=1.8)
                plotted.extend(errors)
            axis.set(xlabel="Stored ROM entries" if rom else "Polynomial degree",ylabel="Maximum absolute error" if maximum else "Mean absolute error",title="Whole-test maximum" if maximum else "Whole-test mean")
            if rom:
                axis.set_xscale("log",base=2)
                entries = [int(name.split("_")[1]) for name in roms]
                ticks = entries if len(entries)<=7 else entries[::2]
                axis.set_xticks(ticks,[f"{value:,}" for value in ticks],rotation=30)
            else:
                axis.set_xticks(range(5))
            axis.grid(alpha=.2)
            axis.spines[["top","right"]].set_visible(False)
            axis.legend(frameon=False)
        for axis in axes:
            comparison.signed_error_ticks(axis,0,max(plotted,default=0))
        group_folder = model_folder(series[0][1][0]) if len(series)==1 else "00_comparisons"
        destination = directory/"05_accuracy_vs_model_size"/group_folder/filename
        note = "Uses saved whole-test statistics. Means: uniform population. Maxima: largest across uniform and boundary populations. No plotting bins."
        finish(figure,destination,title,evaluation,note)
        positive = [value for value in plotted if value > 0]
        if positive:
            lower = 10 ** numpy.floor(numpy.log10(min(positive)))
            upper = 10 ** numpy.ceil(numpy.log10(max(positive)))
            ticks = numpy.geomspace(lower,upper if upper>lower else lower*10,6)
            for axis in axes:
                axis.set_yscale("log")
                axis.set_ylim(ticks[0],ticks[-1])
                axis.set_yticks(ticks)
                axis.set_yticklabels([number_label(value,0) for value in ticks])
                axis.minorticks_off()
            finish(figure,destination.with_stem(destination.stem+"_log_scale"),title+" (logarithmic error scale)",evaluation,"Saved whole-test statistics. Equal vertical spacing represents equal error ratios; lower values mean better accuracy.")


def save_coefficients(directory):
    figure,axis = pyplot.subplots(figsize=(13,4))
    axis.axis("off")
    cells = [[degree,*[f"{values[power]:,}" if power<len(values) else "" for power in range(5)]] for degree,values in comparison.SOLLYA_COEFFICIENTS.items()]
    table=axis.table(cellText=cells,colLabels=["Degree","Constant","f","f squared","f cubed","f to power 4"],cellLoc="center",loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1,2)
    finish(figure,directory/"00_formulas"/"02_sollya_coefficients.png","Sollya stored coefficient integers","Signed 32-bit coefficients with 24 fractional bits","Divide each integer by 16,777,216 to obtain its coefficient.")


def refresh_derived_tables(output,rows,inputs,predictions):
    coefficient_rows=[]
    for degree,values in comparison.SOLLYA_COEFFICIENTS.items():
        for power,integer in enumerate(values):
            coefficient_rows.append({"degree":degree,"power":power,"exact_decimal":str(comparison.Decimal(integer)/comparison.INPUT_SCALE),"signed_32_bit_integer":integer,"hexadecimal_32_bits":f"{integer & 0xFFFFFFFF:08X}","binary_32_bits":f"{integer & 0xFFFFFFFF:032b}","fractional_bits":24})
    comparison.write_csv(output/"sollya_q24_coefficients.csv",coefficient_rows)
    compact=[]
    for degree in range(5):
        names=(["linear"] if degree==1 else ["cubic"] if degree==3 else [])+[f"maclaurin_{degree}",f"sollya_{degree}"]
        for name in names:
            compact.append({"degree":degree,"model":model_name(name,True),"ideal_maximum_absolute_error":summary_value(rows,name,"mathematical_fractional",True),"ideal_mean_absolute_error":summary_value(rows,name,"mathematical_fractional",False),"q24_maximum_absolute_error":summary_value(rows,name,"hardware_fractional",True),"q24_mean_absolute_error":summary_value(rows,name,"hardware_fractional",False)})
    comparison.write_csv(output/"degree_accuracy_comparison.csv",compact)
    comparison.write_csv(output/"polynomial_accuracy_summary.csv",[row for row in rows if row["domain"]=="mathematical_fractional" and not row["model"].startswith("bram_")])
    stride=max(1,len(inputs)//4000)
    comparison.write_csv(output/"polynomial_value_samples.csv",[{"fractional_exponent":float(inputs[position]),"actual_2_to_f":float(numpy.exp2(inputs[position])),**{name:float(values[position]) for name,values in predictions.items() if not name.startswith("bram_")}} for position in range(0,len(inputs),stride)])


def render_results(output,refresh_tables=False,tables=None):
    configuration=json.loads((output/"run_configuration.json").read_text())
    if configuration["output_fractional_bits"]!=24:
        raise ValueError("This plot layout expects signed 32-bit Q24 comparison results.")
    preserved={path:path.read_bytes() for path in output.glob("*.csv")} if not refresh_tables else {}
    rows=list(csv.DictReader((output/"accuracy_summary.csv").open()))
    for row in rows:
        for key,value in row.items():
            if key not in ("model","domain","population") and value:
                row[key]=float(value)
    if tables is None:
        storage_rows=list(csv.DictReader((output/"bram_storage.csv").open()))
        table_path=next((Path(row["source"]) for row in storage_rows if int(row["entries"])==1024),comparison.DEFAULT_TABLE_PATH)
        tables={size:comparison.make_table(size,table_path) for size in configuration["rom_sizes"]}
    uniform,boundaries=comparison.input_vectors(262144,max(tables))
    encoded=numpy.unique(numpy.concatenate((uniform,boundaries)))
    inputs=encoded/comparison.INPUT_SCALE
    references=numpy.exp2(inputs)
    bins=configuration["plot_bin_count"]
    identifiers=encoded*bins//comparison.INPUT_SCALE
    positions=numpy.concatenate(([0],numpy.flatnonzero(numpy.diff(identifiers))+1))
    counts=numpy.diff(numpy.concatenate((positions,[len(encoded)])))
    centres=(identifiers[positions]+.5)/bins
    ideal=comparison.mathematical_models(inputs,tables)
    fixed={name:comparison.fractional_fixed_point(name,encoded,tables[int(name.split("_")[1])] if name.startswith("bram_") else None)/comparison.OUTPUT_SCALE for name in ideal}
    names=sorted(ideal,key=lambda name:(0 if name=="linear" else 1 if name=="cubic" else 2 if name.startswith("maclaurin_") else 3 if name.startswith("sollya_") else 4,int(name.split("_")[1]) if "_" in name else 0))
    colours={name:pyplot.get_cmap("tab20")(position%20) for position,name in enumerate(names)}
    try:
        comparison.save_formula_table(output)
        save_coefficients(output/"images"/"02_fixed_point")
        for branch,domain,predictions,evaluation in (("01_ideal","mathematical_fractional",ideal,"Ideal formulas before fixed-point arithmetic truncation"),("02_fixed_point","hardware_fractional",fixed,"Fixed point: signed 32-bit Q24 output; no integer shift")):
            directory=output/"images"/branch
            fixed_point=branch=="02_fixed_point"
            errors={name:predictions[name]-references for name in names}
            means={name:numpy.add.reduceat(numpy.abs(errors[name]),positions)/counts for name in names}
            maxima={name:numpy.maximum.reduceat(numpy.abs(errors[name]),positions) for name in names}
            for category in CATEGORIES:
                save_error_category(directory,category,inputs,centres,errors,means,maxima,names,colours,evaluation,fixed_point,bins)
                print(f"Saved {branch}/{category}: individual models and all-model comparison.",flush=True)
            save_model_size_plots(directory,rows,domain,names,evaluation,fixed_point)
            print(f"Saved {branch}/05_accuracy_vs_model_size: linear and logarithmic whole-test comparisons.",flush=True)
        comparison.save_accuracy_tables(output,rows,configuration["exhaustive_q24_coverage"])
        if refresh_tables:
            refresh_derived_tables(output,rows,inputs,ideal)
    finally:
        for path,data in preserved.items():
            if path.read_bytes()!=data:
                path.write_bytes(data)
    guide="""# Accuracy plot folders

The two main folders are 01_ideal and 02_fixed_point. Each contains:

- 01_signed_error: individual-input signed error. Positive means overestimate; negative means underestimate.
- 02_absolute_error: individual-input error magnitude.
- 03_mean_absolute_error: mean error magnitude per display bin.
- 04_maximum_absolute_error: maximum error magnitude per display bin.
- 05_accuracy_vs_model_size: whole-test error versus ROM entry count or polynomial degree, with separate mean and maximum panels. Each comparison has a linear-scale and a log-scale image.
- 06_accuracy_tables: whole-test percentage-error and absolute-error tables.

Each error category has 00_comparisons, 01_research, 02_maclaurin, 03_sollya and 04_rom subfolders. Individual plots are grouped by model family; 00_comparisons contains 00_all_models_comparison.png. ROM individual-input plots include a zoom of the first four address intervals. These use a display subset of 262144 uniform inputs plus ROM boundaries and neighbours; they do not replace the complete accuracy sweep.

The model-size folder also groups images into 00_comparisons, 02_maclaurin, 03_sollya and 04_rom, keeping linear and log-scale views together. The accuracy-table folder has 01_absolute_error and 02_percentage_error subfolders. Formula folders have no further nesting.

The model-size comparisons use the saved whole-test statistics, not display bins. ROM entries and polynomial degree use separate horizontal axes. Research models appear as individual points at degrees 1 and 3.

00_formulas contains the full formula table in both branches. The fixed-point branch also includes the stored Sollya coefficient table. The formula table describes the polynomials before intermediate/output truncation. Full data and run settings remain at the results root. The Q24 research cubic is a modified version retaining its linear term at Q24; previous Q8 FPGA measurements are separate.
"""
    (output/"images"/"README.md").write_text(guide)
    print("Plot organisation complete; saved accuracy statistics were used without rerunning the full sweep.",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Regenerate error-category plots from saved accuracy results.")
    parser.add_argument("--results-directory",type=Path,default=Path(__file__).resolve().parent/"results")
    render_results(parser.parse_args().results_directory.resolve())
